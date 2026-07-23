import pandas as pd

df = pd.read_csv('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_dataset/canonical_dataset.csv')

print("=== Malaria (B54) Sample ===")
print(df[df['icd_candidate'] == 'B54'][['icd_candidate', 'symptom_string', 'drug_name']].head(3).to_string(index=False))

print("\n=== Chikungunya (A92.0) Sample ===")
print(df[df['icd_candidate'] == 'A92.0'][['icd_candidate', 'symptom_string', 'drug_name']].head(3).to_string(index=False))

print("\n=== Tuberculosis (A15) Sample ===")
print(df[df['icd_candidate'] == 'A15'][['icd_candidate', 'symptom_string', 'drug_name']].head(3).to_string(index=False))

