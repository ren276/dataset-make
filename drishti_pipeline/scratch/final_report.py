import pandas as pd
df = pd.read_csv('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_dataset/canonical_dataset.csv')
print("Total rows:", len(df))
print("\nTier Distribution:")
print(df['tier'].value_counts(normalize=True).sort_index().apply(lambda x: f"{x:.2%}"))

print("\nCandidate selections (target rare diseases + fevers):")
c = df['icd_candidate'].value_counts()
targets = ['A90', 'B54', 'A01.0', 'A92.0', 'A09', 'D50', 'F41.0', 'E05.9']
for t in targets:
    print(f"{t}: {c.get(t, 0)}")

print("\nTop 10 ICD candidates:")
print(c.head(10))
