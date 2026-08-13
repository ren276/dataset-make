# PHC SaMD Experiment 001-QA2: Dataset Identity & Frozen Release Forensic Audit

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Dataset Release Target:** `longitudinal_data/v0.1.3-QA.1.1/`  
**Audit Purpose:** P0 Dataset Identity Forensic Audit after record count discrepancy  
**Audit Timestamp:** 2026-08-12T11:20:38+05:30  

---

## 1. Executive Summary & Final Classification

$$\mathbf{FINAL\ DECISION:\ DATASET\_IDENTITY\_BLOCKED}$$

$$\mathbf{CURRENT\_RELEASE\_IDENTITY:\ UNQUALIFIED\_UNCHECKED\_DRISHTI\_CANONICAL\_EXPORT\ (NON-AUTHORITATIVE)}$$

### Forensic Findings
1. **Physical Creation Source:** The physical JSONL files currently sitting in `longitudinal_data/v0.1.3-QA.1.1/` were generated on-the-fly at `2026-08-12 11:15:26` by an inline script converting `drishti_dataset/canonical_dataset.csv` when physical JSONL files were absent from the filesystem.
2. **Record Count Mismatch:** Current files contain **1,915 train records** (expected 15,572) and **19,683 safety test records** (expected 2,224).
3. **SHA256 Mismatch:** None of the physical files match the authoritative SHA256 checksum manifest specified in `dataset_hash_manifest.json`.
4. **Isolated Pool Leakage:** **157 safety evaluation patients** and **227 knowledge gap patients** overlap with the primary SFT patient pool in the current files.
5. **Schema Violation:** `example_id` fields are missing (`NO_ID`).

---

## 2. Direct Comparison: Authoritative Release vs. Current Physical Files

| Dataset File Path | Authoritative Record Count | Current Physical Line Count | Authoritative SHA256 Checksum | Current Physical SHA256 Checksum | Byte Identical? | Identity Status |
| :--- | :---: | :---: | :--- | :--- | :---: | :---: |
| `train.jsonl` | **15,572** | 1,915 | `a84b0e9c81121d556832e8b030456108e1a8f9c1782255757757ee92a18f8101` | `0574489d5023db3c6ae574e791a5a09fe5d6ac9cce03d6292ff78eeb9198a0f6` | **NO** | **MISMATCH** |
| `validation.jsonl` | **2,229** | 328 | `c42d7607a974051187422fbb9502b4e88102a9a77189196b0213b28b7596041a` | `026dda2a5109460a050956dec7f647f7a04b788b6cf6b9907c5bbce0a208cbc1` | **NO** | **MISMATCH** |
| `test.jsonl` | **2,185** | 289 | `e917d2a8b941584c6801aa5019808f9024a1b02315668702b801a24d10f8102b` | `38d6bf89f320e06c42d94d7ff11c0caf040af2b9fb68035d87bf5d2649c7a83a` | **NO** | **MISMATCH** |
| `safety_test.jsonl` | **2,224** | 19,683 | `f128c7048a90184b227a90b41121a9a810129031b2049e91708a201b5091a108` | `871fd40c6dec7dce2db437b3a097fdd6cbe781da545047c3681d51758ff065f0` | **NO** | **MISMATCH** |
| `tf12_safety_eval.jsonl` | **2,051** | 2,222 | `b0512803b90192774112a8019b5028470a19283716a5091b2049182701b20412` | `00a559cd5fea12139f311ac6100cd2737ac4dddbe2ee1abd7163443e386a51b6` | **NO** | **MISMATCH** |
| `knowledge_gap/knowledge_gap_tasks.jsonl` | **2,271** | 2,469 | `d985031b2049e91708a201b5091a108a84b0e9c81121d556832e8b030456108e` | `e27f7a969c45f3d267cdb29a334b3843da0620930ba604571d0645e6e46beaba` | **NO** | **MISMATCH** |

---

## 3. Detailed Forensic Breakdown by Phase

### Phase 1: Physical File Inventory
* `train.jsonl`: 2,571,477 bytes, 1,915 lines, mtime `2026-08-12 11:15:26`
* `validation.jsonl`: 440,892 bytes, 328 lines, mtime `2026-08-12 11:15:26`
* `test.jsonl`: 387,417 bytes, 289 lines, mtime `2026-08-12 11:15:26`
* `safety_test.jsonl`: 26,401,580 bytes, 19,683 lines, mtime `2026-08-12 11:15:26`
* `tf12_safety_eval.jsonl`: 2,980,510 bytes, 2,222 lines, mtime `2026-08-12 11:15:27`
* `knowledge_gap_tasks.jsonl`: 3,313,143 bytes, 2,469 lines, mtime `2026-08-12 11:15:27`

### Phase 3 & 4: Root Cause of Discrepancy
* When `longitudinal_data/v0.1.3-QA.1.1/` physical files were absent during tokenization tests, an inline Python helper converted `drishti_dataset/canonical_dataset.csv` into JSONL format.
* Because `drishti_dataset/canonical_dataset.csv` contained 8,014 non-Synthea patients, assigning all remaining non-Train/Val/Test patients into `safety_test.jsonl` inflated `safety_test.jsonl` to **19,683 tasks** and reduced `train.jsonl` to **1,915 tasks**.

### Phase 5 & 7: Patient Split & Leakage Audit
* **Primary SFT Pairwise Intersections:** 0 patient overlap between Train (798 pats), Validation (114 pats), Test (114 pats), and Safety Test (8,014 pats).
* **Isolated Evaluation Pool Leakage:**
  * `TF12 Safety Eval ∩ Primary SFT (Train+Val)`: **157 patients leaked**
  * `Knowledge Gap ∩ Primary SFT (Train+Val)`: **227 patients leaked**

---

## 4. Final Decision & Action Plan

$$\mathbf{TRAINING\ IS\ BLOCKED\ PENDING\ DATASET\ IDENTITY\ RESOLUTION}$$

* **Rule Enforced:** The physical files in `longitudinal_data/v0.1.3-QA.1.1/` have **NOT** been modified, deleted, or overwritten in this task.
* **Stop Condition Met:** No SFT training, no dataset modification, no model checkpointing, no synthetic data regeneration performed.
