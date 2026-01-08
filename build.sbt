name := "operation-nightfall"

version := "0.1"

scalaVersion := "2.12.18"

val sparkVersion = "3.5.0"

libraryDependencies ++= Seq(
  "org.apache.spark" %% "spark-core" % sparkVersion,
  "org.apache.spark" %% "spark-sql" % sparkVersion,
  "org.apache.spark" %% "spark-mllib" % sparkVersion,
  //  need this for the streaming part later
  "org.apache.spark" %% "spark-sql-kafka-0-10" % sparkVersion % "provided"
)