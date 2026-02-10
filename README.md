# Operation Nightfall

Real-time communication pipeline for military operations, featuring ML-powered message classification and priority-based alerting.

## Overview

This system processes coalition military communications in real-time, using a Random Forest classifier to identify message priority levels. CRITICAL messages trigger immediate visual alerts for rapid response.

**Key Features:**
- Synthetic data generation for UK-Saudi coalition communications
- NLP pipeline with TF-IDF feature extraction
- Random Forest classifier achieving 84% accuracy
- Spark Structured Streaming for real-time processing
- Visual CRITICAL alert dashboard

## Prerequisites

- **Java 17** (OpenJDK recommended)
- **sbt 1.9+** (Scala Build Tool)
- **Python 3.10+** with pip

## Quick Start

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate Training & Streaming Data
```bash
python3 data_generator.py
```
Generates 50,000 training records and 100,000 streaming records.

### 3. Train the Classifier
```bash
sbt "runMain TrainClassifier"
```
Trains a Random Forest model and saves it to `models/priority_classifier`.

### 4. Run the Streaming Pipeline

**Terminal 1** - Start the processor:
```bash
mkdir -p incoming_stream
sbt "runMain StreamingProcessor"
```

**Terminal 2** - Start the simulator:
```bash
python3 stream_simulator.py
```

CRITICAL alerts will appear in Terminal 1 as messages are processed.

## Project Structure

```
├── data_generator.py       # Generates synthetic military communications
├── stream_simulator.py     # Simulates real-time message arrival
├── src/main/scala/
│   ├── TrainClassifier.scala      # ML model training
│   └── StreamingProcessor.scala   # Real-time classification & alerts
├── build.sbt               # Scala/Spark dependencies
└── requirements.txt        # Python dependencies
```

## Priority Levels

| Priority | Distribution | Description |
|----------|--------------|-------------|
| CRITICAL | 15% | Immediate threat to life, requires instant response |
| HIGH | 25% | Urgent tactical situations |
| MEDIUM | 35% | Standard operational updates |
| LOW | 25% | Routine administrative messages |

## License

For authorized use only.
