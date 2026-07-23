import sys
import os
sys.path.insert(0, '/media/sandesh/extra-ssd/dataset/dataset-make/drishti_pipeline')
import config

for entry in config.ICD_MAPPING:
    if "candidates" not in entry:
        print(f"Missing candidates: {entry['params']}")
