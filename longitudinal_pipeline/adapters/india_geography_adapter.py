import yaml
import random
from pathlib import Path
from typing import Dict

class IndiaGeographyAdapter:
    def __init__(self, config_path: Path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
    def adapt(self, patient_id: str, seed: int) -> Dict[str, str]:
        rng = random.Random(f"{patient_id}_{seed}_geography")
        
        state = rng.choice(self.config['states'])
        district = rng.choice(state['districts'])
        block = rng.choice(district['blocks'])
        
        village_num = rng.randint(1, 100)
        village = f"{block} Village {village_num}"
        pincode = str(rng.randint(111111, 999999))
        
        return {
            "state": state['name'],
            "state_code": state['code'],
            "district": district['name'],
            "block": block,
            "village": village,
            "pincode": pincode
        }
