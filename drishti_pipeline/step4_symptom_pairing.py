"""
drishti_pipeline/step4_symptom_pairing.py
==========================================
Reads the tiered DataFrame from step3, samples symptoms + drug/dosage per
row from the mapped condition's pools, and adds symptom_string +
symptom_signal_strength + drug_name + drug_dosage.

Symptom/drug sampling:
  - Calls config.resolve_condition(abnormal_params, patient_id, encounter_date)
    -- the SAME deterministic resolver step3 uses for icd_chapter/icd_block/
    icd_candidate. This is critical: for multi-candidate ICD_MAPPING entries
    (e.g. {"fever_pattern","pulse_high"} -> dengue/malaria/typhoid/...), step3
    and step4 must resolve to the identical condition for a given row, or the
    label (icd_candidate) and the symptoms/drug sampled here could silently
    disagree (row labeled "dengue" but drug pool sampled from "malaria").
  - Within the resolved condition's symptom_pool, samples up to 3 symptoms
    without replacement (this sub-sampling can still use a row-local seed --
    it only affects flavor-text variety, not which condition was selected).
  - "no symptoms" always maps to "nonspecific".

Output adds: symptom_string, symptom_signal_strength, drug_name, drug_dosage,
             pediatric_referral_flag
Writes: tiered_with_symptoms_{seed}.csv to scratch.
"""

import sys
import random
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drishti_pipeline import config

SYNONYMS = {
    "breathlessness": ["shortness of breath", "dyspnea", "trouble breathing", "gasping for air"],
    "fatigue": ["tiredness", "exhaustion", "lethargy", "weakness"],
    "chest tightness": ["chest pressure", "chest heaviness", "chest discomfort"],
    "palpitations": ["racing heart", "fluttering chest", "heart pounding"],
    "severe headache": ["splitting headache", "throbbing head", "pounding headache"],
    "dizziness": ["lightheadedness", "faintness", "feeling woozy"],
    "joint pain": ["arthralgia", "aching joints", "joint soreness"],
    "abdominal pain": ["stomach ache", "belly pain", "tummy ache"],
    "nausea": ["feeling sick", "queasiness", "stomach upset"],
    "loss of appetite": ["poor appetite", "not hungry", "reduced eating"],
    "sweating": ["perspiration", "diaphoresis", "sweats"],
}

# Pre-compute global pool for distractors
GLOBAL_SYMPTOMS = []
for entry in config.ICD_MAPPING + [config.FALLBACK_ENTRY]:
    if "candidates" in entry:
        for c in entry["candidates"]:
            for s in c.get("symptom_pool", []):
                if s not in GLOBAL_SYMPTOMS:
                    GLOBAL_SYMPTOMS.append(s)
    else:
        for s in entry.get("symptom_pool", []):
            if s not in GLOBAL_SYMPTOMS:
                GLOBAL_SYMPTOMS.append(s)

def sample_symptom(abnormal_params_str: str, patient_id: str, encounter_date: str,
                    seed_offset: int = 0) -> tuple:
    """
    Given abnormal_params as a comma-separated string, resolve the SAME
    condition step3 resolved for this row (via config.resolve_condition,
    keyed on patient_id+encounter_date) and sample one (symptom_text,
    signal_strength) pair and one (drug_name, drug_dosage) pair from that
    condition's pools.
    Returns (symptom_string, symptom_signal_strength, drug_name, drug_dosage).
    """
    param_set = frozenset()
    if abnormal_params_str and abnormal_params_str != "normal":
        param_set = frozenset(p.strip() for p in abnormal_params_str.split(","))
    resolved = config.resolve_condition(param_set, patient_id, encounter_date)
    pool = resolved.get("symptom_pool", [("no symptoms", "nonspecific")])

    if not pool:
        return ("no symptoms", "nonspecific", "None", "None")

    # Row-local seed for symptom-text VARIETY only -- the condition itself
    # was already fixed above by resolve_condition, deterministically.
    r = random.Random(hash(abnormal_params_str) + seed_offset)

    num_to_sample = r.randint(2, min(4, len(pool)))
    # We want to sample without replacement, so use r.sample
    chosen_symptoms = r.sample(pool, num_to_sample)
    
    # Inject a distractor phrase ~10% of the time
    if r.random() < 0.10 and len(GLOBAL_SYMPTOMS) > 0:
        distractor = r.choice(GLOBAL_SYMPTOMS)
        if distractor not in chosen_symptoms:
            chosen_symptoms.append(distractor)
            r.shuffle(chosen_symptoms)
            
    symptom_strs = []
    strengths = []
    for c in chosen_symptoms:
        s = c[0]
        # Lexical noise (synonyms) ~20% of the time
        if s in SYNONYMS and r.random() < 0.20:
            s = r.choice(SYNONYMS[s])
        symptom_strs.append(s)
        strengths.append(c[1])

    # Determine highest strength
    if "strong" in strengths:
        max_strength = "strong"
    elif "supportive" in strengths:
        max_strength = "supportive"
    else:
        max_strength = "nonspecific"

    symptom_string = " | ".join(symptom_strs)

    # Sample drug from the SAME resolved condition's prescription pool
    drug_pool = resolved.get("prescription_pool", [("None", "None")])
    if not drug_pool:
        drug_pool = [("None", "None")]
    chosen_drug = r.choice(drug_pool)

    return symptom_string, max_strength, chosen_drug[0], chosen_drug[1]


def run(tiered_df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """
    Full step4: adds symptom_string and symptom_signal_strength to the tiered DataFrame.
    Returns the augmented DataFrame.
    Writes tiered_with_symptoms_{seed}.csv to scratch.
    """
    print(f"  [step4] Adding symptom pairing for seed={seed}, rows={len(tiered_df)}")

    if tiered_df.empty:
        return tiered_df

    df = tiered_df.copy()

    symptoms = []
    strengths = []
    drug_names = []
    drug_dosages = []
    pediatric_flags = []
    
    for i, (_, row) in enumerate(df.iterrows()):
        sym, strength, drug_n, drug_d = sample_symptom(
            str(row.get("abnormal_params", "")),
            str(row.get("patient_id", "")),
            str(row.get("encounter_date", "")),
            seed_offset=i,
        )

        age = int(row.get("age_at_encounter", 18))
        if age < 18:
            drug_n = "None"
            drug_d = "None"
            pediatric_flags.append(True)
        else:
            pediatric_flags.append(False)
            
        symptoms.append(sym)
        strengths.append(strength)
        drug_names.append(drug_n)
        drug_dosages.append(drug_d)

    df["symptom_string"] = symptoms
    df["symptom_signal_strength"] = strengths
    df["drug_name"] = drug_names
    df["drug_dosage"] = drug_dosages
    df["pediatric_referral_flag"] = pediatric_flags

    # Validate signal strength values
    invalid_strengths = df[~df["symptom_signal_strength"].isin(config.VALID_SIGNAL_STRENGTHS)]
    if not invalid_strengths.empty:
        print(f"  [step4] WARNING: {len(invalid_strengths)} rows with invalid signal_strength "
              f"— coercing to 'nonspecific'")
        df.loc[~df["symptom_signal_strength"].isin(config.VALID_SIGNAL_STRENGTHS),
               "symptom_signal_strength"] = "nonspecific"

    # Write to scratch
    config.PIPELINE_SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.PIPELINE_SCRATCH_DIR / f"tiered_with_symptoms_{seed}.csv"
    df.to_csv(out_path, index=False)
    print(f"  [step4] Symptom distribution: "
          f"strong={sum(1 for s in strengths if s == 'strong')}, "
          f"supportive={sum(1 for s in strengths if s == 'supportive')}, "
          f"nonspecific={sum(1 for s in strengths if s == 'nonspecific')}")
    print(f"  [step4] Wrote {len(df)} rows -> {out_path.name}")
    return df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Step 4: Symptom pairing")
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()

    input_path = config.PIPELINE_SCRATCH_DIR / f"tiered_{args.seed}.csv"
    if not input_path.exists():
        print(f"ERROR: tiered_{args.seed}.csv not found — run step3 first", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(input_path, dtype={"patient_id": str})
    result = run(df, seed=args.seed)
    print(result[["abnormal_params", "symptom_string", "symptom_signal_strength", "drug_name", "drug_dosage"]].head(10))
