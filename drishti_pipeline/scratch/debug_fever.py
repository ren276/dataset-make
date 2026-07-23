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
target_set = frozenset({"fever_pattern"})
best_match_rows = []
for _, row in assessed.iterrows():
    if row["fever_pattern_flag"]:
        abn_set = frozenset(row["_abnormal_list"])
        best = config.lookup_icd_entry(abn_set)
        if best.get("params") == target_set:
            best_match_rows.append(row)

best_match_df = pd.DataFrame(best_match_rows)
print(f"Rows where {{'fever_pattern'}} is the BEST match: {len(best_match_df)}")

if len(best_match_df) > 0:
    selected_counts = {}
    for _, row in best_match_df.iterrows():
        abn_set = frozenset(row["_abnormal_list"])
        patient_id = str(row.get("patient_id", ""))
        encounter_date = str(row.get("encounter_date", ""))
        selected = config.resolve_condition(abn_set, patient_id, encounter_date)
        tag = selected.get("condition_tag", "UNKNOWN")
        selected_counts[tag] = selected_counts.get(tag, 0) + 1
    print(f"\nRealized selections for {{'fever_pattern'}} matches: {selected_counts}")

