import pandas as pd
df = pd.read_csv('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_dataset/canonical_dataset.csv')
ped = df[(df['age_at_encounter'] < 18) & (df['drug_name'].notna()) & (df['drug_name'] != 'None')]
print("Pediatric rows with drugs in canonical:", len(ped))
if len(ped) > 0:
    print(ped[['age_at_encounter', 'drug_name', 'pediatric_referral_flag']].head())
