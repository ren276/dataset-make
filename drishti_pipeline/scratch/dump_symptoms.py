import sys
from pathlib import Path
sys.path.insert(0, str(Path('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_pipeline').resolve()))
import config

pools = []
for entry in config.ICD_MAPPING + [config.FALLBACK_ENTRY]:
    if "candidates" in entry:
        for c in entry["candidates"]:
            pools.append((c.get("condition_tag", "unknown"), c.get("symptom_pool", [])))
    else:
        pools.append((entry.get("icd_candidate") or entry.get("differential_candidates", ["unknown"])[0], entry.get("symptom_pool", [])))

for tag, pool in pools:
    print(f"--- {tag} ---")
    for s in pool:
        print(f"  {s[0]} ({s[1]})")
