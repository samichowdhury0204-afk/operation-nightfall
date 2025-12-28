#!/usr/bin/env python3
"""
Operation NIGHTFALL - Data Generator
Generates synthetic military comms data for UK-Saudi coalition simulation,
on an counterterrorism operation. 

Outputs:
1. training_data.csv this is labeled data for MLlib
2. streaming_data.json - this is unlabeled data for spark streaming
3. sample_data.csv - the small sample for verification.
"""

# Import libraries

import csv
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# --- Configuration ---

SEED = 42
random.seed(SEED)

# Output is relative to the script location. 
OUTPUT_DIR = Path(__file__).resolve().parent / "data"

TRAINING_RECORDS = 50_000
STREAMING_RECORDS = 100_000
SAMPLE_RECORDS = 1_000

# sImulation window: 48 hours. Pretending it happened in feb 2024 (leap year - I had a birthday date).
START_TIME = datetime(2024, 2, 27, 0, 0, 0, tzinfo=timezone.utc)
END_TIME = datetime(2024, 2, 29, 0, 0, 0, tzinfo=timezone.utc)
TIME_DELTA_SECONDS = int((END_TIME - START_TIME).total_seconds())

# operation zone centred around the Monica Partridge building in Nottingham. 
LAT_MIN, LAT_MAX = 52.85, 53.04
LNG_MIN, LNG_MAX = -1.30, -1.10

# ---  Units involved for the joint operation --- 

UK_UNITS = [f"{team}-{n}" for team in ("Alpha", "Bravo", "Charlie") for n in range(1, 7)]
SAUDI_UNITS = [f"{team}-{n}" for team in ("Falcon", "Eagle") for n in range(1, 7)]
ALL_UNITS = UK_UNITS + SAUDI_UNITS 

#Set priorities and corresponding weights
PRIORITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
PRIORITY_WEIGHTS = [0.15, 0.25, 0.35, 0.25]

#Types of messages
MESSAGE_TYPES = ["CONTACT", "MEDICAL", "LOGISTICS", "INTEL", "ROUTINE"]

# Probability of message type with each priority.
##change weights if the ml can't differentiate
PRIORITY_MESSAGE_TYPE_MAP: dict[str, list[tuple[str, float]]] = {
"CRITICAL": [("CONTACT", 0.50), ("MEDICAL", 0.30), ("INTEL", 0.15), ("LOGISTICS", 0.03), ("ROUTINE", 0.02)],
"HIGH":     [("INTEL", 0.40), ("CONTACT", 0.30), ("MEDICAL", 0.15), ("LOGISTICS", 0.10), ("ROUTINE", 0.05)],
    "MEDIUM":   [("LOGISTICS", 0.40), ("ROUTINE", 0.25), ("INTEL", 0.20), ("MEDICAL", 0.10), ("CONTACT", 0.05)],
    "LOW":      [("ROUTINE", 0.55), ("LOGISTICS", 0.25), ("INTEL", 0.10), ("MEDICAL", 0.05), ("CONTACT", 0.05)],
}

# --- Message templates ---

ENGLISH_MESSAGES: dict[tuple[str, str], list[str]] = {
    # CRITICAL
    ("CRITICAL", "CONTACT"):   [
        "Taking fire from multiple positions! Request immediate CAS!",
        "Ambush! Contact north-east, at least 12 hostiles with RPGs!",
        "IED detonated on convoy route. Vehicle disabled. Under fire!",
        "Troops in contact! Grid reference {grid}. Requesting QRF!",
        "Heavy contact at checkpoint. Perimeter breached! NEED BACKUP NOW!",
        "Pinned down by sniper fire. Cannot advance. Request suppressive fire.",
    ],
    ("CRITICAL", "MEDICAL"):   [
        "CASEVAC urgent! Two T1 casualties, GSW to chest and abdomen.",
        "Mass casualty event! IED blast, 5 wounded, 2 critical. Need MEDEVAC!",
        "Man down! Arterial bleed, applying tourniquet. Need extraction ASAP!",
        "Multiple casualties from mortar strike. Medical supplies exhausted.",
    ],
    ("CRITICAL", "INTEL"):     [
        "Confirmed VBIED heading towards checkpoint Delta. ETA 5 minutes!",
        "HVT positively identified at grid {grid}. Awaiting strike authority.",
        "Intercepted comms indicate imminent attack on FOB. All units alert!",
    ],
    ("CRITICAL", "LOGISTICS"): [
        "Ammunition critically low! Down to last magazine. Resupply NOW!",
        "Fuel tanker hit. Total loss. Route compromised.",
    ],
    ("CRITICAL", "ROUTINE"):   [
        "All stations, all stations — REDCON 1. This is not a drill.",
    ],

    # HIGH
    ("HIGH", "CONTACT"):       [
        "Enemy spotted, 800m south-west.  squad-sized element.",
        "Suspicious vehicle approaching checkpoint. Weapons visible.",
        "Drone overhead. Possible hostile reconnaissance.",
        "Movement detected in treeline. Probable enemy OP.",
    ],
    ("HIGH", "INTEL"):         [
        "Suspicious movement in Sector 4. Possible staging area.",
        "HUMINT source reports weapons cache at grid {grid}.",
        "Unidentified personnel observed crossing border at dawn.",
        "Intercepted radio traffic suggests enemy repositioning to the east.",
        "Requesting orders. New intel suggests target has relocated.",
    ],
    ("HIGH", "MEDICAL"):       [
        "One T2 casualty — shrapnel wound to left leg. Stable but needs evac.",
        "Heat casualty. Soldier unconscious. IV fluids administered.",
    ],
    ("HIGH", "LOGISTICS"):     [
        "Requesting emergency resupply: ammo, water, batteries.",
        "Route Bravo compromised. Rerouting logistics convoy via Route Delta.",
    ],
    ("HIGH", "ROUTINE"):       [
        "Elevated threat level. All patrols adopt enhanced posture.",
        "Requesting QRF standby. Situation developing in Sector 7.",
    ],

    # MEDIUM
    ("MEDIUM", "LOGISTICS"):   [
        "Resupply needed: MREs for 30 personnel.",
        "Vehicle maintenance required. Engine overheating.",
        "Request water resupply at grid {grid}.",
    ],
    ("MEDIUM", "ROUTINE"):     [
        "Position check: holding at grid {grid}.",
        "Shift rotation complete.",
        "Weather update- sandstorm expected.",
    ],
    ("MEDIUM", "INTEL"):       [
        "Local nationals report unusual activity.",
        "UAV feed shows vehicle tracks.",
    ],
    ("MEDIUM", "MEDICAL"):     [
        "Requesting medical resupply: bandages and morphine",
    ],
    ("MEDIUM", "CONTACT"):     [
        "Heard distant gunfire to the south. Not in our AO. Monitoring.",
    ],

    # LOW
    ("LOW", "ROUTINE"):     [
        "Radio check. Lima Charlie. Over.",
        "Routine patrol complete. Sector clear. RTB.",
        "All clear. No activity to report.",
    ],
    ("LOW", "LOGISTICS"):      [
       "Mail delivery received.",
        "Equipment inventory complete.",
    ],
}

# Arabic messages — Saudi units only
# 5%

# Saudi Unit Messages (Arabic)
# 5% of messages will use these to simulate coalition comms
ARABIC_MESSAGES = {
    "CRITICAL": [
        "نحن تحت نيران كثيفة! نحتاج دعم فوري!",  #Under heavy fire
        "كمين! اشتباك من الجهة الشمالية!",      #Ambush
        "انفجار عبوة ناسفة! إصابات متعددة!",     #IED explosion
    ],
    "HIGH": [
        "رصد تحركات مشبوهة في القطاع ٤",        # Suspsuspicious  movement
        "مركبة مجهولة تقترب بسرعة",             #unkown vehicle approaching fast
    ],
    "MEDIUM": [
        "نحتاج إلى إعادة تزويد بالوقود",        # need refueling
        "صيانة مطلوبة للمركبة الثانية",         #Maintenance required
    ],
    "LOW": [
        "دورية روتينية، المنطقة آمنة",          #Routine patrol, secure
        "فحص الاتصالات. الإشارة واضحة",         #Comms check, clear
    ]}



# --- helper functions ---

def get_random_timestamp():
    offset = random.randint(0, TIME_DELTA_SECONDS)
    ts = START_TIME + timedelta(seconds=offset)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")

def get_gps():
    # Random point within border box
    lat = round(random.uniform(LAT_MIN, LAT_MAX), 6)
    lng = round(random.uniform(LNG_MIN, LNG_MAX), 6)
    return lat, lng

def get_grid_ref():
    return f"{random.randint(1000, 9999)} {random.randint(1000, 9999)}"

def generate_message(unit_id, priority, msg_type):
    # Determine if we should switch to Arabic for Saudi units
    # Logic: If unit is Saudi (Falcon/Eagle), small chance of Arabic comms
    is_arabic = False
    
    is_saudi = unit_id.startswith(("Falcon", "Eagle"))
    
    # 5% global arabic rate approx
    if is_saudi and random.random() < 0.15:
        # Check if we have arabic templates for this priority
        if priority in ARABIC_MESSAGES:
            is_arabic = True
            return random.choice(ARABIC_MESSAGES[priority]), is_arabic

    # Default to English
    key = (priority, msg_type)
    
    # Fallback logic if specific (Priority, Type) tuple doesn't exist
    if key not in ENGLISH_MESSAGES:
        # Just pick a random message from the priority group
        possible_keys = [k for k in ENGLISH_MESSAGES.keys() if k[0] == priority]
        if not possible_keys:
             # Super fallback
             return "Radio check. Over.", False
        key = random.choice(possible_keys)
    
    template = random.choice(ENGLISH_MESSAGES[key])
    
    # Fill dynamic fields
    msg = template.replace("{grid}", get_grid_ref())
    return msg, is_arabic

def generate_record():
    unit = random.choice(ALL_UNITS)
    priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS, k=1)[0]
    
    # Select message type based on priority weights
    type_options = PRIORITY_MESSAGE_TYPE_MAP[priority]
    types, weights = zip(*type_options)
    msg_type = random.choices(types, weights=weights, k=1)[0]
    
    lat, lng = get_gps()
    text, is_arabic = generate_message(unit, priority, msg_type)
    
    return {
        "timestamp": get_random_timestamp(),
        "unit_id": unit,
        "gps_lat": lat,
        "gps_lng": lng,
        "message_text": text,
        "priority": priority,
        "message_type": msg_type,
        "_is_arabic": is_arabic # Internal flag, remove before save
    }

# --- Main Execution ---

def main():
    print(f"Starting Data Generation for Operation NIGHTFALL...")
    print(f"Seed: {SEED}")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate Training Data (CSV)
    print(f"Generating {TRAINING_RECORDS} training records...")
    training_data = []
    for _ in tqdm(range(TRAINING_RECORDS)):
        training_data.append(generate_record())
        
    # Sort chronologically
    training_data.sort(key=lambda x: x['timestamp'])
    
    # Save Training Data
    # Note: Using utf-8-sig so Excel opens Arabic characters correctly
    train_df = pd.DataFrame([{k:v for k,v in r.items() if not k.startswith('_')} for r in training_data])
    train_path = OUTPUT_DIR / "training_data.csv"
    train_df.to_csv(train_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {train_path}")
    
    # 2. Generate Streaming Data (JSON)
    print(f"Generating {STREAMING_RECORDS} streaming records...")
    streaming_data = []
    for _ in tqdm(range(STREAMING_RECORDS)):
        streaming_data.append(generate_record())
        
    streaming_data.sort(key=lambda x: x['timestamp'])
    
    # Save Streaming Data as NDJSON (one object per line) for Spark
    stream_path = OUTPUT_DIR / "streaming_data.json"
    with open(stream_path, 'w', encoding='utf-8') as f:
        for record in tqdm(streaming_data):
            # Clean internal flags
            clean_rec = {k:v for k,v in record.items() if not k.startswith('_')}
            f.write(json.dumps(clean_rec, ensure_ascii=False) + '\n')
    print(f"Saved: {stream_path}")

    # 3. Create Sample
    sample_path = OUTPUT_DIR / "sample_data.csv"
    train_df.head(SAMPLE_RECORDS).to_csv(sample_path, index=False, encoding="utf-8-sig")
    print(f"Saved sample: {sample_path}")
    
    print("\nGeneration Complete.")
    print(f"English/Arabic Split (Training):")
    arabic_count = sum(1 for r in training_data if r['_is_arabic'])
    print(f"Arabic Messages: {arabic_count} ({arabic_count/TRAINING_RECORDS:.1%})")

if __name__ == "__main__":
    main()