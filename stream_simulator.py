#!/usr/bin/env python3
# Operation NIGHTFALL - Stream Simulator
# Feeds JSON data into the incoming_stream directory to simulate real-time traffic.

import json
import random
import shutil
import time
import uuid
import os
from pathlib import Path
from tqdm import tqdm

# Config
SEED = 42
random.seed(SEED)

BASE_DIR = Path(__file__).parent
INPUT_FILE = BASE_DIR / "data" / "streaming_data.json"
OUTPUT_DIR = BASE_DIR / "incoming_stream"

# Speed Control
# Sleep between 0.01s and 0.05s to average ~50 msgs/sec
MIN_DELAY = 0.01 
MAX_DELAY = 0.05

# Burst Mode (Simulate combat intensity)
BURST_CHANCE = 0.05
BURST_SIZE = 10

def setup_dirs():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

def write_message(line):
    try:
        record = json.loads(line)
        # Create unique filename based on timestamp and random UUID
        # Spark Streaming picks up new files in the directory
        ts = record.get("timestamp", "unknown").replace(":", "-")
        fname = f"msg_{ts}_{uuid.uuid4().hex[:8]}.json"
        
        with open(OUTPUT_DIR / fname, "w", encoding="utf-8") as f:
            f.write(line.strip())
            
    except Exception as e:
        print(f"Error writing message: {e}")

def simulate_stream():
    print(f"Reading from: {INPUT_FILE}")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        messages = f.readlines()
    
    total = len(messages)
    print(f"Loaded {total} messages.")
    
    setup_dirs()
    print(f"Streaming to: {OUTPUT_DIR}")
    print("Press Ctrl+C to stop early.\n")
    
    i = 0
    pbar = tqdm(total=total, unit="msg")
    
    try:
        while i < total:
            # 5% chance to send a 'burst' of messages instantly
            if random.random() < BURST_CHANCE:
                limit = min(i + BURST_SIZE, total)
                for j in range(i, limit):
                    write_message(messages[j])
                
                count = limit - i
                pbar.update(count)
                i = limit
            else:
                # Normal mode
                write_message(messages[i])
                pbar.update(1)
                i += 1
            
            # Simulate network/processing latency
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            
    except KeyboardInterrupt:
        print("\nStream stopped by user.")
    finally:
        pbar.close()
        print(f"\nFinished. {i} messages written to {OUTPUT_DIR}")

if __name__ == "__main__":
    simulate_stream()