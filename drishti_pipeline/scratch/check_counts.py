import pandas as pd

pre = pd.read_csv('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_pipeline/scratch/tiered_with_symptoms_46.csv', dtype=str, keep_default_na=False)
post = pd.read_csv('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_dataset/canonical_dataset.csv', dtype=str, keep_default_na=False)

targets = ['A90', 'A91', 'B54', 'A01.0', 'A92.0', 'A15', 'D50', 'F41.0', 'E05.9']

print(f"{'Condition':<10} | {'Pre-Dedup (27k)':<15} | {'Post-Dedup (22.2k)':<18} | {'Retention %'}")
print("-" * 65)
for t in targets:
    pre_count = (pre['icd_candidate'] == t).sum()
    post_count = (post['icd_candidate'] == t).sum()
    retention = (post_count / pre_count * 100) if pre_count > 0 else 0
    print(f"{t:<10} | {pre_count:<15} | {post_count:<18} | {retention:.1f}%")
