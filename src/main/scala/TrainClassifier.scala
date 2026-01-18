/**
 * Operation NIGHTFALL - Priority Classifier
 * this script trains  a Random Forest model to classify message priority.
 *
 * Current Accuracy:  84.44%
 */

import org.apache.spark.sql.SparkSession
import org.apache.spark.ml.Pipeline
import org.apache.spark.ml.classification.RandomForestClassifier
import org.apache.spark.ml.evaluation.MulticlassClassificationEvaluator
import org.apache.spark.ml.feature.{HashingTF, IDF, IndexToString, StringIndexer, StopWordsRemover, Tokenizer}
import org.apache.spark.sql.functions.when
import scala.util.{Try, Success, Failure}

object TrainClassifier {

  def main(args: Array[String]): Unit = {

    val spark = SparkSession.builder()
      .appName("Operation Nightfall - Training")
      .master("local[*]")
      .getOrCreate()

    //Silence the logs (too much stuff otherwise)
    spark.sparkContext.setLogLevel("WARN")
    import spark.implicits._

    println("-- Starting Model Training --")

    // 1. Load Data
    val dataPath = "data/training_data.csv"
    val df = Try(spark.read.option("header", "true").option("inferSchema", "true").csv(dataPath)) match {
      case Success(d) => d
      case Failure(e) => 
        println(s"ERROR: Could not load $dataPath. Check file path.")
        sys.exit(1)
    }

    println(s"Loaded ${df.count()} records.")

    // 2. Preprocessing Pipeline
    // Using standard NLP stages: Tokenize -> Remove Stop Words -> TF-IDF

    val tokenizer = new Tokenizer().setInputCol("message_text").setOutputCol("words")

    val remover = new StopWordsRemover().setInputCol("words").setOutputCol("filtered_words")

    //Initially tried 65536 features but hit OOM on local machine, was too much.
    // REDUCED to 4096 which gives similar accuracy but faster training.
    val hashingTF = new HashingTF()
      .setInputCol("filtered_words")
      .setOutputCol("raw_features")
      .setNumFeatures(4096) 

    val idf = new IDF().setInputCol("raw_features").setOutputCol("features")

    //StringIndexer, this sorts by frequency descending. 
    // 0.0 = Most common (MEDIUM), 1.0 = Next (LOW), etc.
    val labelIndexer = new StringIndexer()
      .setInputCol("priority")
      .setOutputCol("label")
      .setHandleInvalid("keep")

    // 3. Model Definition
    // Using Random Forest as it handles the sparse TF-IDF vectors better than Logistic Regression
    val rf = new RandomForestClassifier()
      .setLabelCol("label")
      .setFeaturesCol("features")
      .setNumTrees(30)   // Reduced from 50 for speed
      .setMaxDepth(8)
      .setSeed(42)

    val labelConverter = new IndexToString()
      .setInputCol("prediction")
      .setOutputCol("predicted_priority")
      .setLabels(Array("MEDIUM", "LOW", "HIGH", "CRITICAL")) // Manual mapping based on frequency

    // 4. Train
    val Array(trainingData, testData) = df.randomSplit(Array(0.8, 0.2), seed = 42)
    
    val pipeline = new Pipeline().setStages(Array(tokenizer, remover, hashingTF, idf, labelIndexer, rf))

    println("Training Random Forest...")
    val startTime = System.nanoTime()
    val model = pipeline.fit(trainingData)
    val duration = (System.nanoTime() - startTime) / 1e9d
    println(f"Training finished in $duration%.2f seconds")

    // 5.EVALUATE
    val predictions = model.transform(testData)
    val evaluator = new MulticlassClassificationEvaluator()
      .setLabelCol("label")
      .setPredictionCol("prediction")
      .setMetricName("accuracy")

    val accuracy = evaluator.evaluate(predictions)
    println(f"Model Accuracy: ${accuracy * 100}%.2f%%")

    // POTENTIALLY ADD CONFUSION MATRIX

    // 6. Save
    // overwrites existing model to allow retraining
    model.write.overwrite().save("models/priority_classifier")
    println("Model saved to models/priority_classifier")

    spark.stop()
  }
}