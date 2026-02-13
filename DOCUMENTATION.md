# Operation Nightfall - Documentation

## Project Description

Operation Nightfall is a real-time military communications processing pipeline which classifies live incoming comms by priority level and surfaces alerts classified as 'Critical' immediately to a military control room. The system simulates UK-Saudi coalition operations and identifies urgent situations requiring immediate response (eg: mass casualty events, IED detonations). The pipeline consists of four components:

- **Data generation (python)** - 50,000 labelled training records and 100,000 unlabelled streaming records simulating realistic military communications with timestamps, GPS coordinates, unit identifiers, and most importantly message content.
- **Model training (Scala / Spark MLlib)** - Here resides a complete NLP pipeline using Tokeniser, StopWordsRemover, HashingTF and IDF for feature extraction, which feeds into a random forest classifier that achieves an 84% accuracy on priority classification.
- **Stream processing (Scala/Spark Structured Streaming)** – Incoming messages are continuously monitored. The trained model is loaded, and each message is classified in real time. Filters for critical priority alerts.
- **Alert dashboard** - Displays critical messages with formatting including unit identifier, timestamp, and message content. This is designed to aid in rapid operator response.

I chose this scenario because it's a genuine Big Data challenge – it's high volume, time sensitive data. Military communication is usually noisy and urgent, which makes it prime for combining machine learning and stream processing.

## What is out of scope?

**Decryption:** We've made the assumption that messages are already decrypted at ingress. Complex cryptography is not part of this data engineering scope. This is due to being pragmatic with the timeline, although cryptography is a part of big data security (especially in the military). Including it here would not be achievable with stream velocity – the spark pipeline is designed for high-throughput analytics. Cryptographic processing would create an artificial bottleneck, which might obscure the performance metrics of actual data processing logic.

**Full GUI:** The output is a terminal based 'Control Centre' dashboard, rather than a web based React/Angular frontend. Data engineering focuses on the pipeline rather than the 'prettiness'. This is aimed at a technical audience as the control centre is full of analysts working alongside military comms personnel.

## Learning Aim

The aim was to move beyond standard batch processing and apply big data theory to a real time environment, using a new (but achievable to learn) programming language. In particular I:

- **Transitioned from Python to Scala:** I am comfortable with Python, but wanted to challenge myself by implementing the core processing logic in Scala. By way of this, I understood the benefits of strong typing and functional programming within the Apache Spark ecosystem.
- **Simulate high velocity data:** Rather than a static dataset, I wanted to delve more into the 'velocity' area of big data. The data streaming method mimics the 'bursty' nature of real-world military comms.

## Project Data

The data has **velocity** (constant comms coming in), **volume** (100,000+ voice notes handled), and varies in **veracity** (non-critical messages, indirect threats). The data is synthetic for security and privacy reasons (real world military data is not permitted on non-MOD assets). The data has **variety** too, as it is a semi-structured JSON containing a mix of fixed fields, and unstructured natural language (message text). It also includes bilingual content (English and Arabic). It has a lot of **value** in that routine traffic is filtered to highlight critical threats, displaying the military unit, which reduces cognitive load on commanders and potentially saves lives.

## Business Questions

- **Threat detection:** Can we automatically identify high priority combat events (eg 'Man down', 'taking fire')?
- **Noise reduction:** Can we filter out routine logistical chatter (eg 'Radio check'), to prevent alert fatigue in the control centre?
- **Strategic asset:** Can this project serve as a 'strategic asset', such that further capability can be built from it, such as cloud computing and more robust ML models?

## Resources – Cloud, On-Premise & Costing

Current implementation is at zero cost, as it only requires an IDE and local Spark installation. This zero cost solution was sufficient for proof of concept, because the simulated stream volume fits within local memory. We would want to avoid cloud billing during the development phase. This mitigates for being limited by laptop RAM.

One way to scale beyond this is by distributing the operations units amongst multiple different control centre personnel (scale horizontally rather than vertically). We could also deploy this to Azure Databricks. A cluster of 3x Standard D4s nodes (general purpose) would only cost £0.40/hour. Since operations may happen back to back, we can re-train the ML model on terabytes of historical data in minutes (using distributed Spark), rather than days, which pushes updated models to the front line faster.

## Reflection

Going for Scala and real time streaming was a struggle but rewarding at the same time. I challenged myself by not sticking just to what I knew (Python batch processing), and going for a more complex method (Scala/real time streaming). I also managed to, as opposed to just module taught content, compare learning methods. I combined between YouTube videos, websites (more similar to books), and getting an AI to teach me basic Scala syntax. I found that books and articles were more comprehensive, videos were quite good but relatively concise, and 'AI tutoring' was super concise, which can be effective but leave out important 'whys' and comparisons - unless you prompt it differently.

What went well was the successful implementation of the structured streaming pipeline in Scala. The syntax in Scala was initially a bit daunting, because it's stricter and functional programming concepts were foreign. When I tried to run Scala code with sbt, the application crashed and had odd errors related to Java module access, that required research. My streaming processor also crashed with errors, because Spark attempted to read a file that was already written. I adjusted to add permissive JSON mode to solve this.

This project has shifted my career focus, as I now know that data engineering is a lot about handling how live systems can go wrong (eg latency issues, my programme trying to read an incomplete file). I feel more confident applying for roles that require Spark/Scala now. I also successfully integrated an ML model in a streaming context for the first time. This required me to understand how to serialise Spark pipelines (PipelineModel), applying this to data in motion without causing bottlenecks.

I aimed for the highest grade band and in doing so I exposed myself to concepts that were genuinely new and seemed very advanced. Scala was not so hard but more so debugging the streaming issues independently. Overall, this has been a whirlwind that I will look back on fondly.

### Data Variability Considerations

One significant limitation of the current implementation is the constrained template pool used for message generation. The data_generator.py script relies on approximately 50-60 fixed English message templates distributed across different priority and message_type combinations, plus around 9 Arabic templates. This means that while we generate 50,000 training records and 100,000 streaming records, the actual linguistic diversity is significantly limited. The model is essentially learning to classify from a finite set of approximately 60 distinct messages (with minor variations from the dynamic {grid} placeholder substitutions).

This limited template approach has both weaknesses and surprising strengths. The primary weakness is **overfitting risk** – the classifier may become highly accurate at recognising these specific 60 message patterns, but struggle when deployed in a real operational environment where messages would be far more varied, using different phrasing, slang, or context-specific terminology. For example, the training data contains "Taking fire from multiple positions!" as a CRITICAL/CONTACT message, but in reality, a soldier might say "We're getting lit up from the north" or "Heavy engagement, need support" – messages that convey the same urgency but with completely different linguistic patterns. The model has never seen these variations during training.

However, there's a plausible scenario where the model could maintain reasonable accuracy even with completely unseen messages. This is because **the core semantic patterns and keywords that define priority levels are often consistent**. Critical messages universally contain high-urgency language like "fire", "casualties", "IED", "MEDEVAC", "ambush" – regardless of the exact phrasing. If a new message contains these high-intensity keywords and urgent phrasing patterns, the TF-IDF feature extraction and Random Forest classifier may still correctly categorise it as CRITICAL, even if the exact sentence structure is novel. The model learns to associate certain vocabulary (weighted by TF-IDF importance) with priority levels, not necessarily memorise exact templates. This explains why transfer learning can work in NLP – semantic meaning often transcends specific wording.

Ideally, the solution would be to **generate truly NEW messages** rather than selecting from templates. This could be achieved through several approaches: (1) using a large language model (LLM) to generate diverse military communications based on scenario prompts, ensuring varied linguistic expression while maintaining realistic context; (2) collecting and anonymising real (or realistic) military exercise transcripts to build a more diverse corpus; or (3) implementing a template expansion system that uses synonym substitution, sentence restructuring, and grammatical variation to create hundreds of unique messages from each base template. For instance, transforming "Taking fire from multiple positions!" into variations like "Under fire from several directions", "Receiving incoming from multiple angles", or "Hostile fire – multiple sources". This would significantly improve the model's generalisation capability and robustness to real-world deployment scenarios where linguistic variation is inevitable.
