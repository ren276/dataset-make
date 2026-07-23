import pandas as pd
df = pd.read_csv('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_pipeline/scratch/tiered_with_symptoms_46.csv')
ped = df[(df['age_at_encounter'] < 18) & (df['drug_name'] != 'None') & (df['drug_name'].notna())]
print("Pediatric rows with drugs:", len(ped))
print(ped[['age_at_encounter', 'drug_name', 'pediatric_referral_flag']].head())
