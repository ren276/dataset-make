from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

@dataclass
class GenerationManifest:
    dataset_make_git_commit: str
    synthea_git_commit: str
    java_version: str
    gradle_version: str
    python_version: str
    pip_freeze: str
    dependency_lock_hash: str
    generation_seed: int
    population_size: int
    age_range: str
    raw_source_hashes: Dict[str, str]
    adaptation_config_hash: str
    clinical_derivation_rules_hash: str
    scenario_rules_hash: str
    kernel_config_hash: str
    task_taxonomy_hash: str
    generator_version: str
    schema_version: str
    dataset_version: str
    generation_start_utc: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

@dataclass
class GenerationLogEntry:
    timestamp_utc: str
    step_name: str
    seed: Optional[int]
    input_row_count: Optional[int]
    output_row_count: Optional[int]
    validation_summary: Dict[str, Any]
    
    @classmethod
    def create(cls, step_name: str, seed: Optional[int] = None, 
               input_rows: Optional[int] = None, output_rows: Optional[int] = None, 
               validation: Dict[str, Any] = None):
        return cls(
            timestamp_utc=datetime.utcnow().isoformat() + "Z",
            step_name=step_name,
            seed=seed,
            input_row_count=input_rows,
            output_row_count=output_rows,
            validation_summary=validation or {}
        )
        
    def to_json_line(self) -> str:
        return json.dumps(asdict(self))
