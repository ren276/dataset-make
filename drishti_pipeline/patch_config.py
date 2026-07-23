import re

with open('config.py', 'r') as f:
    content = f.read()

# Update CANONICAL_COLUMNS
col_match = re.search(r'("symptom_signal_strength",\s*)', content)
if col_match:
    content = content[:col_match.end()] + '"drug_name",\n    "drug_dosage",\n    ' + content[col_match.end():]

# Update CANONICAL_DTYPES
dtype_match = re.search(r'("symptom_signal_strength": "string",\s*)', content)
if dtype_match:
    content = content[:dtype_match.end()] + '"drug_name":             "string",\n    "drug_dosage":           "string",\n    ' + content[dtype_match.end():]

# Define drug pools
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
    'frozenset({"spo2", "bmi"})': '[("Oxygen", "Nightly"), ("CPAP", "Nightly")]',
    'frozenset({"bmi", "pulse_high"})': '[("Metformin", "500mg"), ("Metoprolol", "25mg")]',
    'frozenset({"pulse_high", "pulse_low"})': '[("Amiodarone", "200mg"), ("None", "None")]',
    'frozenset({"bp_systolic"})': '[("Amlodipine", "5mg"), ("Telmisartan", "40mg"), ("Losartan", "50mg")]',
    'frozenset({"bp_diastolic"})': '[("Telmisartan", "40mg"), ("Losartan", "50mg")]',
    'frozenset({"spo2"})': '[("Oxygen", "2L/min"), ("Salbutamol", "100mcg")]',
    'frozenset({"bmi"})': '[("Metformin", "500mg"), ("Atorvastatin", "10mg")]',
    'frozenset({"pulse_high"})': '[("Propranolol", "10mg"), ("Metoprolol", "25mg")]',
    'frozenset({"pulse_low"})': '[("Atropine", "0.5mg"), ("None", "None")]'
}

# Regex to find each dictionary in ICD_MAPPING
# We'll do string replacements block by block
new_content = ""
for line in content.splitlines(True):
    new_content += line
    match = re.search(r'"params": (frozenset\(\{.*?\}\)),', line)
    if match:
        param_str = match.group(1)
        # We know we need to insert prescription_pool into this dict. 
        # But we must insert it after symptom_pool. Let's do a post-processing pass instead.

with open('config.py', 'w') as f:
    f.write(new_content)

