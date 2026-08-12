from dataclasses import dataclass, field, asdict
from typing import Optional, List, Any
import hashlib
import json
from datetime import datetime

def generate_source_fact_id(patient_id: str, fact_category: str, source_file: str, source_row_identifier: str, source_field: str, concept: str, timestamp: str, value: Any) -> str:
    raw = f"{patient_id}|{fact_category}|{source_file or ''}|{source_row_identifier or ''}|{source_field or ''}|{concept or ''}|{timestamp or ''}|{str(value)}"
    return f"fact_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"

def generate_derived_fact_id(patient_id: str, fact_category: str, concept: str, timestamp: str, value: Any, derivation_rule: str, source_facts: List[str], order_matters: bool = False) -> str:
    src_str = ",".join(source_facts) if order_matters else ",".join(sorted(source_facts))
    raw = f"{patient_id}|{fact_category}|{concept or ''}|{timestamp or ''}|{str(value)}|{derivation_rule or ''}|{src_str}"
    return f"fact_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"

def generate_scenario_fact_id(patient_id: str, scenario_rule: str, source_facts: List[str], payload: Any, order_matters: bool = False) -> str:
    src_str = ",".join(source_facts) if order_matters else ",".join(sorted(source_facts))
    payload_str = json.dumps(payload, sort_keys=True) if isinstance(payload, (dict, list)) else str(payload)
    raw = f"{patient_id}|SCENARIO_FACT|{scenario_rule or ''}|{src_str}|{payload_str}"
    return f"fact_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"

def generate_task_id(patient_id: str, scenario_id: str, task_family: str, language: str, input_mode: str, difficulty: str, task_generator_version: str, task_template_version: str = "v1.0") -> str:
    raw = f"{patient_id}|{scenario_id}|{task_family}|{language}|{input_mode}|{difficulty}|{task_generator_version}|{task_template_version}"
    return f"task_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"

@dataclass
class FactProvenance:
    fact_id: Optional[str] = None
    fact_category: str = "SOURCE_FACT" # SOURCE_FACT, DERIVED_FACT, SCENARIO_FACT, KERNEL_OUTPUT, PHYSICIAN_FACT, LLM_GENERATED_TEXT
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    timestamp: Optional[str] = None
    
    # Source Fact specifics
    source_file: Optional[str] = None
    source_field: Optional[str] = None
    source_row_identifier: Optional[str] = None
    source_value: Optional[str] = None
    
    # Derived Fact specifics
    derivation_rule: Optional[str] = None
    
    # Scenario Fact specifics
    scenario_rule: Optional[str] = None
    
    # Kernel Fact specifics
    kernel_version: Optional[str] = None
    
    # Shared provenance
    source_facts: List[str] = field(default_factory=list)
    rule_version: Optional[str] = None
    generator_version: Optional[str] = None
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

@dataclass
class FactRecord:
    provenance: FactProvenance
    fact_type: str # vital, condition, medication, demographic, encounter_metadata
    concept: str
    value: Any = None
    unit: Optional[str] = None
    status: str = "KNOWN" # KNOWN, UNKNOWN, NOT_RECORDED, NOT_APPLICABLE
    medication_layer: Optional[str] = None # MEDICATION_EVENT, PRESCRIPTION_SCENARIO, KERNEL_RECOMMENDATION, PHYSICIAN_APPROVED_PRESCRIPTION
    semantic_role: Optional[str] = None # DIAGNOSIS, CLINICAL_FINDING, SYMPTOM, VITAL_SIGN, LAB_RESULT, etc.

    def to_dict(self):
        return {
            "fact_type": self.fact_type,
            "concept": self.concept,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "medication_layer": self.medication_layer,
            "semantic_role": self.semantic_role,
            **asdict(self.provenance)
        }
        
    @classmethod
    def from_dict(cls, d: dict):
        prov_fields = {k: v for k, v in d.items() if k not in ["fact_type", "concept", "value", "unit", "status", "medication_layer", "semantic_role"]}
        prov = FactProvenance(**prov_fields)
        return cls(
            provenance=prov,
            fact_type=d.get("fact_type"),
            concept=d.get("concept"),
            value=d.get("value"),
            unit=d.get("unit"),
            status=d.get("status", "KNOWN"),
            medication_layer=d.get("medication_layer"),
            semantic_role=d.get("semantic_role")
        )

