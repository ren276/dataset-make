import sys
import pandas as pd
from pathlib import Path

# Add drishti_pipeline to path so we can import config
sys.path.insert(0, str(Path('/media/sandesh/extra-ssd/dataset/dataset-make')))
from drishti_pipeline import config
import drishti_pipeline.step2b_demographic_reweight as step2b
import drishti_pipeline.step3_tiered_generator as step3

pool = step2b.load_accumulated_pool()

assessed = step3.assess_dataframe(pool)
target_set = frozenset({"pulse_high"})
best_match_rows = []
for _, row in assessed.iterrows():
    abn_set = frozenset(row["_abnormal_list"])
    best = config.lookup_icd_entry(abn_set)
    if best.get("params") == target_set:
        best_match_rows.append(row)

print(f"Rows where {{'pulse_high'}} is the BEST match: {len(best_match_rows)} out of {len(pool)}")
