import pandas as pd
df = pd.read_csv('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_dataset/canonical_dataset.csv', dtype=str, keep_default_na=False)
int_cols = ["age_at_encounter"]
for c in int_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int32")

ped = df[(df['age_at_encounter'] < 18)]
print("Total pediatric rows in canonical:", len(ped))
