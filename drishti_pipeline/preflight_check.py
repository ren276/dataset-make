#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import pandas as pd
from collections import defaultdict

import config
import step1_generate as step1
import step2_extract_vitals as step2
import step3_tiered_generator as step3

def run_preflight(pop_per_seed: int = 1000, num_seeds: int = 5):
    print("============================================================")
    print("  DRISHTI Vitals Pipeline PREFLIGHT CHECK")
    print(f"  Generating sample of {num_seeds} seeds, {pop_per_seed} pop/seed...")
    print("============================================================\n")

    # 1. Generate small fast sample
    pool_dfs = []
    for i in range(num_seeds):
        seed = 9990 + i
        print(f"[Sample] Running Synthea for seed={seed} (pop={pop_per_seed})...")
        csv_path = config.PIPELINE_SCRATCH_DIR / f"vitals_raw_{seed}.csv"
        if csv_path.exists():
            print(f"  [Sample] Found existing sample for seed={seed}, skipping generation.")
            df = pd.read_csv(csv_path, dtype={"patient_id": str})
            pool_dfs.append(df)
            continue
            
        ok = step1.run(seed=seed, pop_size=pop_per_seed)
        if not ok:
            print(f"  [!] Step 1 failed for seed={seed}")
            continue
        try:
            step2.run(seed=seed)
        except Exception as e:
            print(f"  [!] Step 2 failed for seed={seed}: {e}")
            continue
            

            
    if not pool_dfs:
        print("ERROR: Failed to generate any sample rows.")
        sys.exit(1)
        
    pool = pd.concat(pool_dfs, ignore_index=True)
    total_raw = len(pool)
    print(f"\n[Sample] Successfully accumulated {total_raw} raw rows.\n")
    
    # 2. Assess abnormal params
    assessed = step3.assess_dataframe(pool)
    
    # 3. Check every key in ICD_MAPPING and FALLBACK_ENTRY
    all_mappings = list(config.ICD_MAPPING)
    if hasattr(config, "FALLBACK_ENTRY") and config.FALLBACK_ENTRY:
        # Fallback entry has params = frozenset()
        all_mappings.append(config.FALLBACK_ENTRY)

    # Pre-compute abnormal param strings for the mappings to map them to rows
    # Note: abnormal_params in the DF is a sorted comma-separated string,
    # but we can just use the frozenset directly via the _abnormal_list column.
    
    # Let's count occurrences of each frozenset of params
    param_set_counts = defaultdict(int)
    for lst in assessed["_abnormal_list"]:
        param_set_counts[frozenset(lst) if lst else frozenset()] += 1
        
    print(f"--- REACHABILITY AND REALIZATION CHECK ---")
    
    errors = []
    warnings = []
    
    # Track raw rows needed to reach MIN_RARE_DISEASE_FLOOR and MIN_GLUCOSE_HIGH_FLOOR
    extrapolation_needed = {}
    glucose_high_hit = 0
    rare_disease_hits = {code: 0 for code in config.RARE_DISEASE_CODES}
    
    for entry in all_mappings:
        req_params = entry["params"]
        req_params_str = ",".join(sorted(list(req_params))) if req_params else "normal (0 params)"
        
        # Rows that EXACTLY match these params
        # Wait, the pipeline maps EXACT MATCHES to the entry.
        # But wait, config.ICD_MAPPING is matched EXACTLY by `resolve_condition`.
        # Let's use `resolve_condition` on all rows to be exactly accurate.
        pass

    # We will just run resolve_condition on all rows and tally the results
    realized_candidates = defaultdict(int)
    for _, row in assessed.iterrows():
        abn_list = row.get("_abnormal_list", [])
        abn_set = frozenset(abn_list) if abn_list else frozenset()
        resolved = config.resolve_condition(abn_set, str(row.get("patient_id", "")), str(row.get("encounter_date", "")))
        
        cand = resolved.get("icd_candidate")
        if cand:
            realized_candidates[cand] += 1
            if cand in rare_disease_hits:
                rare_disease_hits[cand] += 1
        
        if "glucose_high" in abn_set:
            glucose_high_hit += 1

    # Now evaluate every configured candidate
    for entry in all_mappings:
        req_params = entry["params"]
        req_params_str = ",".join(sorted(list(req_params))) if req_params else "normal (0 params)"
        
        # Verify weights sum to 1.0 only for multi-candidate entries
        if "candidates" in entry:
            base_sum = sum(c["weight"] for c in entry["candidates"])
            if not (0.99 <= base_sum <= 1.01):
                errors.append(f"Weights for '{req_params_str}' base candidates sum to {base_sum:.2f} != 1.0")
                
            has_monsoon = any("monsoon_weight" in c for c in entry["candidates"])
            if has_monsoon:
                monsoon_sum = sum(c.get("monsoon_weight", c["weight"]) for c in entry["candidates"])
                if not (0.99 <= monsoon_sum <= 1.01):
                    errors.append(f"Monsoon weights for '{req_params_str}' candidates sum to {monsoon_sum:.2f} != 1.0")
        
        # Check realization of every configured non-null candidate
        # Note: some candidates have icd_candidate=None. We only track non-null.
        # But wait, the prompt says "every weighted candidate inside multi-candidate entries... flag any candidate with 0 realized selections"
        # We can track by condition_tag!
        pass

    # Better approach: track by condition_tag AND params_str to isolate hits per mapping
    realized_condition_tags = defaultdict(int)
    for _, row in assessed.iterrows():
        abn_list = row.get("_abnormal_list", [])
        abn_set = frozenset(abn_list) if abn_list else frozenset()
        resolved = config.resolve_condition(abn_set, str(row.get("patient_id", "")), str(row.get("encounter_date", "")))
        
        tag = resolved.get("condition_tag")
        if tag:
            req_params_str = ",".join(sorted(list(abn_set))) if abn_set else "normal (0 params)"
            realized_condition_tags[(tag, req_params_str)] += 1

    print(f"{'Condition Tag':<40} | {'Expected Params':<40} | {'Realized Sample Count':<25}")
    print("-" * 110)
    
    for entry in all_mappings:
        req_params = entry["params"]
        req_params_str = ",".join(sorted(list(req_params))) if req_params else "normal (0 params)"
        
        candidates = entry.get("candidates", [entry])
        for cand in candidates:
            tag = cand.get("condition_tag")
            if not tag:
                tag = cand.get("icd_candidate") or (cand.get("differential_candidates") or ["unspecified"])[0]
                
            count = realized_condition_tags.get((tag, req_params_str), 0)
            
            print(f"{tag:<40} | {req_params_str:<40} | {count:<25}")
            
            # For single-entry, weight defaults to 1.0 if missing
            weight = cand.get("weight", 1.0)
            if count == 0 and weight > 0:
                errors.append(f"Candidate '{tag}' under '{req_params_str}' has 0 realized selections in {total_raw} sample rows! Unreachable?")

    print("\n--- EXTRAPOLATION FOR FLOORS ---")
    target_rows = 27000 # Default
    multiplier = getattr(config, 'RAW_POOL_MULTIPLIER', 4)
    expected_raw_pool = target_rows * multiplier
    max_passes = expected_raw_pool * 2 # If it requires more than 2x the standard pool, it's unreachable
    
    print(f"Sample Size: {total_raw} rows")
    print(f"Expected Standard Raw Pool: ~{expected_raw_pool} rows")
    
    print("\nRare Disease Extrapolation (Target Floor: {config.MIN_RARE_DISEASE_FLOOR}):")
    for code in config.RARE_DISEASE_CODES:
        hits = rare_disease_hits[code]
        if hits == 0:
            extrapolated = 0
            needed_raw = float('inf')
        else:
            hit_rate = hits / total_raw
            extrapolated = int(hit_rate * expected_raw_pool)
            needed_raw = int(config.MIN_RARE_DISEASE_FLOOR / hit_rate)
            
        print(f"  {code:<6}: Sample={hits:<4} | Expected in standard pool=~{extrapolated:<5} | Est. Raw Rows Needed={needed_raw}")
        if needed_raw > max_passes:
            errors.append(f"Rare disease {code} requires ~{needed_raw} raw rows to hit floor of {config.MIN_RARE_DISEASE_FLOOR}, which is >2x the standard pool size ({expected_raw_pool}). Increase its weight or base rate.")
            
    # Glucose High
    gh_hits = glucose_high_hit
    if gh_hits == 0:
        gh_needed = float('inf')
    else:
        gh_hit_rate = gh_hits / total_raw
        gh_extrapolated = int(gh_hit_rate * expected_raw_pool)
        gh_needed = int(config.MIN_GLUCOSE_HIGH_FLOOR / gh_hit_rate)
    
    print(f"\nGlucose High (Target Floor: {config.MIN_GLUCOSE_HIGH_FLOOR}):")
    print(f"  Sample={gh_hits:<4} | Expected in standard pool=~{gh_extrapolated:<5} | Est. Raw Rows Needed={gh_needed}")
    if gh_needed > max_passes:
        errors.append(f"glucose_high requires ~{gh_needed} raw rows to hit floor of {config.MIN_GLUCOSE_HIGH_FLOOR}, which is >2x the standard pool size ({expected_raw_pool}). Increase biometrics occurrence.")

    print("\n============================================================")
    if errors:
        print("  [FAIL] Preflight Check failed with the following errors:")
        for e in errors:
            print(f"    - {e}")
        print("============================================================")
        sys.exit(1)
    else:
        print("  [PASS] All mappings are reachable and weights are valid.")
        print("============================================================")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preflight check for DRISHTI Vitals Pipeline")
    parser.add_argument("--pop-per-seed", type=int, default=1000, help="Synthea population per seed (default: 1000)")
    parser.add_argument("--num-seeds", type=int, default=5, help="Number of seeds to sample (default: 5)")
    args = parser.parse_args()
    
    run_preflight(pop_per_seed=args.pop_per_seed, num_seeds=args.num_seeds)
