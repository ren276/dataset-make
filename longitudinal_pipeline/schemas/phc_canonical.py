from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class AilmentEntry:
    id: str
    source_type: str # PATIENT_REPORTED_AILMENT, CLINICIAN_RECORDED_CONDITION, MEASUREMENT, SCENARIO_AILMENT
    measurement_type: str # MEASURABLE, NON_MEASURABLE
    concept: str
    value: Any = None
    unit: Optional[str] = None
    
@dataclass
class PHCEncounter:
    encounter_id: str
    patient_id: str
    timestamp: str
    canonical_encounter_type: str # OPD_NEW, OPD_FOLLOWUP, CHRONIC_REVIEW, etc or UNKNOWN
    age_at_encounter: int
    chief_complaint: Optional[str] = None # explicitly NULL if not from source
    chief_complaint_status: str = "NOT_RECORDED"
    ailments: List[AilmentEntry] = field(default_factory=list)

@dataclass
class PHCPatient:
    patient_id: str
    synthetic_patient_id: str
    biological_sex: str
    state: str
    district: str
    block: str
    village: str
    pincode: str
    full_name: str
    encounters: List[PHCEncounter] = field(default_factory=list)
