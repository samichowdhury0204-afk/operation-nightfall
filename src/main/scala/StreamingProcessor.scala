/**
 * Operation NIGHTFALL - Streaming Processor
 * * 1. Reads JSON stream from incoming_stream/
 * 2. Adds dummy 'priority' column to satisfy pipeline requirements
 * 3. Classifies using Random Forest model
 * 4. Alerts on CRITICAL messages
 */

import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.types.{StructType, StructField, StringType, DoubleType}
import org.apache.spark.sql.functions.{col, lit}
import org.apache.spark.ml.PipelineModel
import org.apache.spark.ml.feature.IndexToString
import scala.util.{Try, Success, Failure}

object StreamingProcessor {

  def main(args: Array[String]): Unit = {

    val spark = SparkSession.builder()
      .appName("Operation Nightfall - Streaming")
      .master("local[*]")
      .getOrCreate()

    spark.sparkContext.setLogLevel("ERROR")
    import spark.implicits._

    println(">>> INITIALIZING STREAMING PROCESSOR <<<")

    // 1. INPUT SCHEMA
    val messageSchema = new StructType(Array(
      StructField("timestamp",    StringType, true),
      StructField("unit_id",      StringType, true),
      StructField("message_text", StringType, true),
      StructField("gps_lat",      DoubleType, true),
      StructField("gps_lng",      DoubleType, true)
    ))

    // 2. LOAD MODEL
    val modelPath = "models/priority_classifier"
    val model = Try(PipelineModel.load(modelPath)) match {
      case Success(m) => 
        println(s"SUCCESS: Model loaded from $modelPath")
        m
      case Failure(e) =>
        println(s"CRITICAL ERROR: Could not load model. Run TrainClassifier first.")
        sys.exit(1)
    }

    // Label Converter
    // Note: Order based on training frequency (Medium -> High/Low -> Critical)
    // CRITICAL is rarest (15%), so it should be the last index.
    val labelConverter = new IndexToString()
      .setInputCol("prediction")
      .setOutputCol("predicted_priority")
      .setLabels(Array("MEDIUM", "HIGH", "LOW", "CRITICAL"))

    // 3. READ STREAM
    // PERMISSIVE mode skips corrupt/partial JSON instead of crashing
    val rawStream = spark.readStream
      .format("json")
      .schema(messageSchema)
      .option("maxFilesPerTrigger", 1)
      .option("mode", "PERMISSIVE")
      .load("incoming_stream/")

    // 4. PREPARE & CLASSIFY
    // IMPORTANT: The training pipeline expects a 'priority' column to index.
    // The stream doesn't have one, so we add a dummy column to prevent a crash.
    val streamWithDummy = rawStream.withColumn("priority", lit("UNKNOWN"))

    val classified = model.transform(streamWithDummy)
    val labeled = labelConverter.transform(classified)

    // 5. ALERT LOGIC — select fields for output
    val alerts = labeled.select(
      $"timestamp",
      $"unit_id",
      $"predicted_priority",
      $"message_text"
    )

    // ANSI colour codes
    val RED   = "\u001B[31m"
    val BOLD  = "\u001B[1m"
    val RESET = "\u001B[0m"
    val SEP   = RED + "═" * 80 + RESET

    println(">>> STREAMING STARTED. WATCH FOR CRITICAL ALERTS... <<<")

    // 6. OUTPUT VIA foreachBatch — silent unless CRITICAL
    val query = alerts.writeStream
      .outputMode("append")
      .option("checkpointLocation", "checkpoints/streaming_processor")
      .foreachBatch { (batchDF: DataFrame, batchId: Long) =>
        try {
          // Cache to avoid re-reading the source (prevents FileNotFoundException)
          val cached = batchDF.cache()

          val criticalRows: Array[Row] = cached
            .filter(col("predicted_priority") === "CRITICAL")
            .collect()

          if (criticalRows.nonEmpty) {
            println(SEP)
            println(s"$RED$BOLD  ⚠  CRITICAL ALERTS — Batch $batchId  ⚠ $RESET")
            println(SEP)

            criticalRows.foreach { row =>
              val ts   = Option(row.getAs[String]("timestamp")).getOrElse("N/A")
              val unit = Option(row.getAs[String]("unit_id")).getOrElse("UNKNOWN")
              val msg  = Option(row.getAs[String]("message_text")).getOrElse("<empty>")
              println(s"$RED$BOLD [!!! CRITICAL ALERT !!!] $RESET $RED Unit: $unit | Time: $ts $RESET")
              println(s"$RED   ↳ $msg $RESET")
            }

            println(SEP)
            println()
          }

          cached.unpersist()
          ()
        } catch {
          case e: Exception =>
            System.err.println(s"[WARN] Batch $batchId skipped: ${e.getMessage}")
        }
      }
      .start()

    query.awaitTermination()
  }
}