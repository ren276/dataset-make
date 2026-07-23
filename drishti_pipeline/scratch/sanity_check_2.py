import pandas as pd
df = pd.read_csv('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_dataset/canonical_dataset.csv')
for code in ['D50', 'F41.0', 'E05.9', 'A15']:
    print(f"\n=== {code} Sample ===")
    print(df[df['icd_candidate'] == code][['icd_candidate', 'symptom_string', 'drug_name']].head(3).to_string(index=False))
