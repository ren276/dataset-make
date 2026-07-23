import sys
import pandas as pd
from pathlib import Path

# Add drishti_pipeline to path so we can import config
sys.path.insert(0, str(Path('/media/sandesh/extra-ssd/dataset/dataset-make')))
from drishti_pipeline import config
import drishti_pipeline.step2b_demographic_reweight as step2b
import drishti_pipeline.step3_tiered_generator as step3

pool = step2b.load_accumulated_pool()
# just sample 10000 rows to be fast
pool = pool.head(10000)

assessed = step3.assess_dataframe(pool)

counts = {}
for _, row in assessed.iterrows():
    abn_set = frozenset(row["_abnormal_list"])
    patient_id = str(row.get("patient_id", ""))
    encounter_date = str(row.get("encounter_date", ""))
    
    # We just resolve the condition for every row and count D50, F41.0, E05.9
    resolved = config.resolve_condition(abn_set, patient_id, encounter_date)
    icd = resolved.get("icd_candidate")
    if icd in ["D50", "F41.0", "E05.9"]:
        counts[icd] = counts.get(icd, 0) + 1

print(f"In a sample of 10,000 rows, realized counts:")
for icd, count in counts.items():
    print(f"  {icd}: {count} (~{count/10000:.2%} of pool)")

