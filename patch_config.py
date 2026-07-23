import re
import os

filepath = 'drishti_pipeline/config.py'

with open(filepath, 'r') as f:
    content = f.read()

# Update CANONICAL_COLUMNS
col_match = re.search(r'("symptom_signal_strength",\s*)', content)
if col_match and '"drug_name"' not in content:
    content = content[:col_match.end()] + '"drug_name",\n    "drug_dosage",\n    ' + content[col_match.end():]

# Update CANONICAL_DTYPES
dtype_match = re.search(r'("symptom_signal_strength": "string",\s*)', content)
if dtype_match and '"drug_name"' not in content[dtype_match.end()-20:dtype_match.end()+200]:
    content = content[:dtype_match.end()] + '"drug_name":             "string",\n    "drug_dosage":           "string",\n    ' + content[dtype_match.end():]


prescription_map = {
    'frozenset({"bp_systolic", "bp_diastolic", "bmi", "pulse_high"})': '[("Amlodipine + Telmisartan", "5mg + 40mg"), ("Metoprolol + Amlodipine", "50mg + 5mg")]',
    'frozenset({"bp_systolic", "bp_diastolic", "spo2"})': '[("Furosemide", "40mg"), ("Nitroglycerin", "0.4mg")]',
    'frozenset({"bp_systolic", "bp_diastolic", "bmi"})': '[("Telmisartan", "40mg"), ("Amlodipine", "5mg"), ("Metformin", "500mg")]',
    'frozenset({"bp_systolic", "spo2", "pulse_high"})': '[("Salbutamol", "100mcg"), ("Oxygen", "2L/min"), ("Amlodipine", "5mg")]',
    'frozenset({"spo2", "pulse_high", "bmi"})': '[("Oxygen", "2L/min"), ("CPAP", "Nightly"), ("Metformin", "500mg")]',
    'frozenset({"bp_systolic", "bp_diastolic"})': '[("Amlodipine", "5mg"), ("Losartan", "50mg"), ("Telmisartan", "40mg")]',
    'frozenset({"bp_systolic", "spo2"})': '[("Furosemide", "40mg"), ("Oxygen", "2L/min")]',
    'frozenset({"bp_systolic", "bmi"})': '[("Amlodipine", "5mg"), ("Metformin", "500mg")]',
    'frozenset({"bp_systolic", "pulse_high"})': '[("Metoprolol", "50mg"), ("Atenolol", "25mg")]',
    'frozenset({"bp_diastolic", "spo2"})': '[("Furosemide", "20mg"), ("Oxygen", "2L/min")]',
    'frozenset({"bp_diastolic", "bmi"})': '[("Telmisartan", "40mg"), ("Atorvastatin", "10mg")]',
    'frozenset({"spo2", "pulse_high"})': '[("Salbutamol", "100mcg"), ("Paracetamol", "500mg")]',
    'frozenset({"spo2", "bmi"})': '[("Oxygen", "2L/min"), ("CPAP", "Nightly")]',
    'frozenset({"bmi", "pulse_high"})': '[("Metformin", "500mg"), ("Metoprolol", "25mg")]',
    'frozenset({"pulse_high", "pulse_low"})': '[("Amiodarone", "200mg"), ("None", "None")]',
    'frozenset({"bp_systolic"})': '[("Amlodipine", "5mg"), ("Telmisartan", "40mg"), ("Losartan", "50mg")]',
    'frozenset({"bp_diastolic"})': '[("Telmisartan", "40mg"), ("Losartan", "50mg")]',
    'frozenset({"spo2"})': '[("Oxygen", "2L/min"), ("Salbutamol", "100mcg")]',
    'frozenset({"bmi"})': '[("Metformin", "500mg"), ("Atorvastatin", "10mg")]',
    'frozenset({"pulse_high"})': '[("Propranolol", "10mg"), ("Metoprolol", "25mg")]',
    'frozenset({"pulse_low"})': '[("Atropine", "0.5mg"), ("None", "None")]'
}

# Now for each dict in ICD_MAPPING, we'll insert the prescription_pool right after symptom_pool
# We'll use regex to find the end of symptom_pool block and insert prescription_pool

def replacer(match):
    full_block = match.group(0)
    if '"prescription_pool":' in full_block:
        return full_block
    
    # find which frozenset this block has
    param_match = re.search(r'"params": (frozenset\(\{.*?\}\)),', full_block)
    if param_match:
        param_str = param_match.group(1)
        pool_str = prescription_map.get(param_str, '[("Paracetamol", "500mg")]')
    else:
        # For FALLBACK_ENTRY
        pool_str = '[("None", "None")]'
        
    # find the end of symptom_pool list
    # The block ends with ], usually.
    # We can just replace '        ],\n    },' with '        ],\n        "prescription_pool": ' + pool_str + ',\n    },'
    # Wait, regex for each dictionary block:
    # A block starts with '{' and ends with '},' (or '}' for FALLBACK_ENTRY)
    return full_block.replace('],\n    }', '],\n        "prescription_pool": ' + pool_str + ',\n    }')

# Find blocks for ICD_MAPPING items
content = re.sub(r'\{\s*"params": frozenset.*?symptom_pool": \[\s*.*?\s*\],\s*\}', replacer, content, flags=re.DOTALL)

# Find FALLBACK_ENTRY
content = re.sub(r'FALLBACK_ENTRY = \{\s*.*?symptom_pool": \[\s*.*?\s*\],\s*\}', replacer, content, flags=re.DOTALL)

with open(filepath, 'w') as f:
    f.write(content)

