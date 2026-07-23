import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from drishti_pipeline.step4_symptom_pairing import sample_symptom

print(sample_symptom("bp_systolic,bp_diastolic,bmi,pulse_high", "smoke-test-patient", "2026-01-15"))
print(sample_symptom("normal", "smoke-test-patient", "2026-01-15"))
