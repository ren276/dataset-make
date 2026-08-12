import yaml
import random
from pathlib import Path
from typing import Dict

class IndiaNamesAdapter:
    def __init__(self, config_path: Path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
    def adapt(self, patient_id: str, sex: str, state_code: str, seed: int) -> Dict[str, str]:
        rng = random.Random(f"{patient_id}_{seed}_names")
        
        if state_code not in self.config['male_first_names']:
            state_code = "MP"
            
        if sex == "M":
            first_name = rng.choice(self.config['male_first_names'][state_code])
        else:
            first_name = rng.choice(self.config['female_first_names'][state_code])
            
        surname = rng.choice(self.config['surnames'][state_code])
        
        return {
            "full_name": f"{first_name} {surname}"
        }
