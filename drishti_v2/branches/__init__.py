"""
drishti_v2/branches/__init__.py
Registry exporting all 33 authored branches.
"""
from . import (
    fever, cough, abdominal_pain, known_hypertension, diarrhoea,
    chest_pain, rash, joint_pain, back_neck_pain, breathlessness,
    known_diabetes, headache, injury, vomiting_nausea, acidity_heartburn,
    urinary_symptoms, cold_sore_throat, weakness_unwell, body_ache, weight_loss,
    oedema, pallor_anaemia, dizziness, itching, skin_infection,
    antenatal_visit, other_not_in_list,
    emergency_convulsions, emergency_unconscious, emergency_bite_sting,
    emergency_poisoning, emergency_heavy_bleeding, emergency_pregnancy_danger
)

ALL_SPECS = {
    "fever": fever.SPEC,
    "cough": cough.SPEC,
    "abdominal_pain": abdominal_pain.SPEC,
    "known_hypertension": known_hypertension.SPEC,
    "diarrhoea": diarrhoea.SPEC,
    "chest_pain": chest_pain.SPEC,
    "rash": rash.SPEC,
    "joint_pain": joint_pain.SPEC,
    "back_neck_pain": back_neck_pain.SPEC,
    "breathlessness": breathlessness.SPEC,
    "known_diabetes": known_diabetes.SPEC,
    "headache": headache.SPEC,
    "injury": injury.SPEC,
    "vomiting_nausea": vomiting_nausea.SPEC,
    "acidity_heartburn": acidity_heartburn.SPEC,
    "urinary_symptoms": urinary_symptoms.SPEC,
    "cold_sore_throat": cold_sore_throat.SPEC,
    "weakness_unwell": weakness_unwell.SPEC,
    "body_ache": body_ache.SPEC,
    "weight_loss": weight_loss.SPEC,
    "oedema": oedema.SPEC,
    "pallor_anaemia": pallor_anaemia.SPEC,
    "dizziness": dizziness.SPEC,
    "itching": itching.SPEC,
    "skin_infection": skin_infection.SPEC,
    "antenatal_visit": antenatal_visit.SPEC,
    "other_not_in_list": other_not_in_list.SPEC,
    "emergency_convulsions": emergency_convulsions.SPEC,
    "emergency_unconscious": emergency_unconscious.SPEC,
    "emergency_bite_sting": emergency_bite_sting.SPEC,
    "emergency_poisoning": emergency_poisoning.SPEC,
    "emergency_heavy_bleeding": emergency_heavy_bleeding.SPEC,
    "emergency_pregnancy_danger": emergency_pregnancy_danger.SPEC,
}
