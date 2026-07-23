# DRISHTI Vitals Pipeline

This directory contains the data generation pipeline for the DRISHTI canonical dataset.

## Quick Start

### 1. Preflight Check (Required)
Always run the preflight check before starting a full dataset regeneration, especially if `config.py` was modified. 
The preflight check generates a small sample pool to validate that every rare disease and mapping condition in `config.ICD_MAPPING` and `config.FALLBACK_ENTRY` is mathematically reachable. It prevents running a multi-hour generation only to discover a gating bug.

```bash
python preflight_check.py
```
*If this fails, adjust the weights or target floors in `config.py` until it passes.*

### 2. Full Regeneration
Once the preflight check passes, run the full multi-phase pipeline to generate the canonical dataset:

```bash
python run_pipeline.py --target-rows 27000 --spot-checks
```

## Note on Tiering Scheme (Rev 7)
Tiers 5/6 (5-6 simultaneous abnormal vitals) occur at <0.001% in Synthea's baseline generation for ambulatory PHC visits — judged clinically implausible to synthetically inject rather than observe, so the tier scheme was collapsed to 4 to reflect only distributions that occur through genuine simulated pathways. Tier 4 (3+ abnormal parameters) now serves as the high acuity ceiling.
