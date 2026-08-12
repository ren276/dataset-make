# PHC SaMD DATASET RECOVERY: EXPERIMENT 001 QA2
## ORIGINAL DATASET-GENERATION MACHINE FORENSIC REPORT

**Date:** 2026-08-12  
**Investigation Target:** Original Dataset-Generation Machine (`sandesh-desktop`)  
**Dataset Version Audited:** `v0.1.3-QA.1.1`  
**Recovery Classification:** `SOURCE_POPULATION_RECOVERABLE`

---

### 1. Original Machine Identity
- **Host / Workspace Root:** `/media/sandesh/extra-ssd/dataset/dataset-make`
- **Storage Mount:** `/media/sandesh/extra-ssd` (NVMe + SSD workspace)
- **Role:** Authoritative Dataset Generation & Lineage Host. (The MedGemma GPU machine with RTX 4070 Ti SUPER is a remote client node).

---

### 2. Dataset Workspace Paths Discovered
The following versioned dataset artifacts and intermediate state directories exist 100% intact on this original machine:
1. `longitudinal_data/v0.1.0`
2. `longitudinal_data/v0.1.1` (Contains frozen 1,140-patient source CSVs and `patient_splits.json`)
3. `longitudinal_data/v0.1.2`
4. `longitudinal_data/v0.1.3` (Contains 1,140 patient fact ledgers)
5. `longitudinal_data/v0.1.3-QA.1`
6. `longitudinal_data/v0.1.3-QA.1.1` (The qualified SFT dataset release)
7. `output_india/` (Sample 561-patient Synthea output directory tracked in git)

---

### 3. Original 1,140-Patient Population Evidence
- **Total Qualified Patient Count:** Exactly **1,140** unique patients.
- **Verification Status:** **VERIFIED 100% MATCH** across:
  - `longitudinal_data/v0.1.1/patient_splits.json` (1,140 entries)
  - `longitudinal_data/v0.1.1/source/csv/patients.csv` (1,140 rows)
  - `longitudinal_data/v0.1.3/fact_ledgers/*.jsonl` (1,140 patient files)
  - `longitudinal_data/v0.1.3-QA.1.1/sft_metadata.jsonl` (1,140 unique `patient_id` values across 22,210 tasks)

---

### 4. Patient Split Evidence
The patient population partition matches the expected specification with 0 cross-split leakage:

| Split | Patient Count | Task Count | Percentage |
| :--- | :--- | :--- | :--- |
| **TRAIN** | 798 | 15,572 | 70% |
| **VALIDATION** | 114 | 2,229 | 10% |
| **TEST** | 114 | 2,185 | 10% |
| **SAFETY_TEST** | 114 | 2,224 | 10% |
| **TOTAL** | **1,140** | **22,210** | **100%** |

- **Authoritative Split Manifest:** `longitudinal_data/v0.1.1/patient_splits.json`

---

### 5. Source Record Availability
All 18 underlying raw source tables for the complete 1,140-patient population exist intact at `/media/sandesh/extra-ssd/dataset/dataset-make/longitudinal_data/v0.1.1/source/csv/`:

| Source Table | Status | Size / Records |
| :--- | :--- | :--- |
| `patients.csv` | **FOUND** | 336 KB (1,140 patients) |
| `encounters.csv` | **FOUND** | 23 MB |
| `conditions.csv` | **FOUND** | 5.9 MB |
| `observations.csv` | **FOUND** | 150 MB |
| `medications.csv` | **FOUND** | 16 MB |
| `procedures.csv` | **FOUND** | 40 MB |
| `allergies.csv` | **FOUND** | 192 KB |
| `immunizations.csv` | **FOUND** | 2.2 MB |
| `careplans.csv` | **FOUND** | 788 KB |
| `organizations.csv` | **FOUND** | 132 KB |
| `providers.csv` | **FOUND** | 158 KB |
| `devices.csv`, `imaging_studies.csv`, `claims.csv`, `supplies.csv`, `payers.csv`, `payer_transitions.csv` | **FOUND** | Complete |

**Source Record Status:** `FOUND` (100% complete for all 1,140 patients).

---

### 6. Explanation of 1,140 vs 561 Patients on GPU Machine
- **Root Cause:** The MedGemma GPU training machine cloned the git repository from `origin/main`.
- In the git repository, the tracked path `output_india/csv/patients.csv` contains a 561-patient sample from a single Synthea run.
- The true production dataset release directory `longitudinal_data/` (which contains the frozen 1,140-patient source records and release `v0.1.3-QA.1.1`) was untracked/ignored in Git.
- Therefore, cloning git on the GPU machine only transferred the 561-patient sample directory, leaving `longitudinal_data/` behind on this original generation host.

---

### 7. Git History Evidence
- **Current HEAD:** `7c87ac6` (`feat: implement longitudinal data pipeline with adapters, schemas, and processing steps`)
- **Working Tree State:** Clean (no reset or modification performed).
- **Git Tracking:** Code (`longitudinal_pipeline/`) and sample outputs (`output_india/`) are tracked; release data directories (`longitudinal_data/`) are kept locally outside git version control.

---

### 8. Pipeline Version Evidence
- **Generator Execution Script:** `longitudinal_pipeline/steps/step20_build_v013_qa11_release.py`
- **Requalification Audit Script:** `longitudinal_pipeline/steps/run_qa11_requalification_audit.py`
- **Full Execution Lineage:**
  - Ingestion & Adaptation: `step02b_source_ingestion_v013.py`, `step04_phc_normalize_v013.py`
  - Scenario & Fact Generation: `step07_scenario_engine_v013.py`, `step09_task_generate_v013.py`
  - Validation & Herding: `step10_validate_v013.py`, `step14_quality_herder_v013.py`
  - Reporting & Release Build: `step18_prepare_training_release_v013.py`, `step19_build_v013_qa1_release.py`, `step20_build_v013_qa11_release.py`
- **Configuration Seed:** `42`

---

### 9. Hash Evidence & Reproducibility
- **Reproducibility Verification Status:** `PASS - ZERO DIFF`
- **Authoritative SHA256 Hashes for `v0.1.3-QA.1.1`:**
  - `train.jsonl`: `8d8d6d9d8087c38c71d8bc4613e4cd64b8f8fa4fae021fb9309d1af553e2ce3f`
  - `validation.jsonl`: `34d221c5a045965a9335a7f68a0105ae232d577496f3224fc4bb6c89f93ad04a`
  - `test.jsonl`: `7d0ea53f5c820475d4e4d97e915f085381a8dfe39593bcf3b56a6c5043545da5`
  - `safety_test.jsonl`: `dba7e517fcc778c2b9113330a02f207604bfda6ce970d914bc70b11d8bf6617b`
  - `tf12_safety_eval.jsonl`: `fe542d48c8c739bfceb156abdfe151bfb1b1485e7d3fb60cb058df17de57e8fa`
  - `knowledge_gap_tasks.jsonl`: `57809cf3c9131ad69a5412e33217cf4a733e5fc99b45c972b99777977954c509`

---

### 10. Recovery Classification

```
SOURCE_POPULATION_RECOVERABLE
```

**Definition:** The exact 1,140-patient population, all 18 underlying source CSV tables, patient split manifests, transformation ledgers, pipeline code, and finalized release artifacts (`v0.1.3-QA.1.1`) exist 100% intact on this original machine.

---

### 11. Exact QA.1.1 Reconstruction & Availability
- **Is Exact Reconstruction / Recovery Possible?** **YES**.
- All 22,210 SFT tasks across Train (15,572), Validation (2,229), Test (2,185), and Safety Test (2,224) are completely present and verified.

---

### 12. Recommended Next Action
1. **Synchronize Dataset to Training GPU Node:** Transfer the `longitudinal_data/` directory (specifically `longitudinal_data/v0.1.3-QA.1.1/` and `longitudinal_data/v0.1.1/source/csv/`) from this machine (`sandesh-desktop`) to the GPU training machine via `rsync`, `scp`, or a compressed tar archive:
   ```bash
   tar -czvf v0.1.3-QA.1.1_release.tar.gz longitudinal_data/v0.1.3-QA.1.1/ longitudinal_data/v0.1.1/source/csv/
   ```
2. **Verify Hashes on GPU Node:** Once transferred to the GPU machine, verify the SHA256 checksums of `train.jsonl`, `validation.jsonl`, `test.jsonl`, and `safety_test.jsonl` against the authoritative values in this report before unblocking SFT model training.
