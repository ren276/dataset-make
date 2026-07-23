import sys
sys.path.insert(0, '/media/sandesh/extra-ssd/dataset/dataset-make/drishti_pipeline')
import pandas as pd
import config
import step3_tiered_generator as step3

pool_dfs = []
for i in range(5):
    seed = 9990 + i
    csv_path = config.PIPELINE_SCRATCH_DIR / f"vitals_raw_{seed}.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"patient_id": str})
        pool_dfs.append(df)

df = pd.concat(pool_dfs)
assessed = step3.assess_dataframe(df)
print("Distribution of param_count in raw pool of size", len(assessed))
print(assessed["_param_count"].value_counts().sort_index())
