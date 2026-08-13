# PHC SaMD EXPERIMENT 001-QA2
## AUTHORITATIVE DATASET RESTORATION REPORT

**Date:** 2026-08-12  
**Source Host:** `sandesh-desktop` (`/media/sandesh/extra-ssd/dataset/dataset-make/`)  
**Target Restoration Directory:** `longitudinal_data/authoritative/v0.1.3-QA.1.1/`  
**Final Classification:** `AUTHORITATIVE_DATASET_RESTORED`

---

### 1. Restoration Overview & Method
The authoritative, previously qualified `v0.1.3-QA.1.1` release (1,140 patients, 22,210 primary SFT tasks) has been restored into a dedicated, clean restoration workspace: `longitudinal_data/authoritative/`.

- **Transfer Method:** `rsync -a` (byte-preserving exact mirror transfer preserving file attributes and byte stream).
- **Contaminated Directory Status:** The existing `longitudinal_data/v0.1.3-QA.1.1/` directory remains **UNTOUCHED AND QUARANTINED** as forensic evidence.

---

### 2. Source vs Target Path Mapping

| Artifact Component | Source Path | Clean Target Path |
| :--- | :--- | :--- |
| **Authoritative Release** | `longitudinal_data/v0.1.3-QA.1.1/` | `longitudinal_data/authoritative/v0.1.3-QA.1.1/` |
| **Source CSV Population** | `longitudinal_data/v0.1.1/source/csv/` | `longitudinal_data/authoritative/v0.1.1/source/csv/` |
| **Patient Split Manifest** | `longitudinal_data/v0.1.1/patient_splits.json` | `longitudinal_data/authoritative/v0.1.1/patient_splits.json` |

---

### 3. Authoritative SHA256 Hash Verification

All transferred files match the expected authoritative SHA256 checksums with 100% byte-for-byte exactness:

| Target File | Expected Authoritative SHA256 | Calculated Target SHA256 | Status |
| :--- | :--- | :--- | :--- |
| `train.jsonl` | `8d8d6d9d8087c38c71d8bc4613e4cd64b8f8fa4fae021fb9309d1af553e2ce3f` | `8d8d6d9d8087c38c71d8bc4613e4cd64b8f8fa4fae021fb9309d1af553e2ce3f` | **PASS** |
| `validation.jsonl` | `34d221c5a045965a9335a7f68a0105ae232d577496f3224fc4bb6c89f93ad04a` | `34d221c5a045965a9335a7f68a0105ae232d577496f3224fc4bb6c89f93ad04a` | **PASS** |
| `test.jsonl` | `7d0ea53f5c820475d4e4d97e915f085381a8dfe39593bcf3b56a6c5043545da5` | `7d0ea53f5c820475d4e4d97e915f085381a8dfe39593bcf3b56a6c5043545da5` | **PASS** |
| `safety_test.jsonl` | `dba7e517fcc778c2b9113330a02f207604bfda6ce970d914bc70b11d8bf6617b` | `dba7e517fcc778c2b9113330a02f207604bfda6ce970d914bc70b11d8bf6617b` | **PASS** |
| `tf12_safety_eval.jsonl` | `fe542d48c8c739bfceb156abdfe151bfb1b1485e7d3fb60cb058df17de57e8fa` | `fe542d48c8c739bfceb156abdfe151bfb1b1485e7d3fb60cb058df17de57e8fa` | **PASS** |
| `knowledge_gap_tasks.jsonl` | `57809cf3c9131ad69a5412e33217cf4a733e5fc99b45c972b99777977954c509` | `57809cf3c9131ad69a5412e33217cf4a733e5fc99b45c972b99777977954c509` | **PASS** |

---

### 4. Record & Patient Count Verification

| Dataset Subset | Expected Record Count | Restored Target Record Count | Patient Count | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TRAIN** | 15,572 | 15,572 | 798 | **PASS** |
| **VALIDATION** | 2,229 | 2,229 | 114 | **PASS** |
| **TEST** | 2,185 | 2,185 | 114 | **PASS** |
| **SAFETY_TEST** | 2,224 | 2,224 | 114 | **PASS** |
| **TOTAL PRIMARY SFT** | **22,210** | **22,210** | **1,140** | **PASS** |
| **TF12 Safety Eval** | 2,051 | 2,051 | - | **PASS** |
| **Knowledge Gap Tasks** | 2,271 | 2,271 | - | **PASS** |

---

### 5. 10-Point Identity Verification Results

1. **SHA256 Equality:** **PASS** (100% byte-identical against authoritative source and expected specification).
2. **Exact JSONL Line Counts:** **PASS** (15,572 Train, 2,229 Val, 2,185 Test, 2,224 Safety Test).
3. **Unique Patient Counts:** **PASS** (798 Train, 114 Val, 114 Test, 114 Safety Test; Total 1,140).
4. **Patient Split Isolation:** **PASS** (0 cross-split patient leakage).
5. **Example ID Uniqueness:** **PASS** (0 ID collisions across 22,210 tasks).
6. **SFT Metadata One-to-One Correspondence:** **PASS** (100% 1-to-1 match across all 22,210 tasks).
7. **TF12 Safety Evaluation Isolation:** **PASS** (2,051 evaluation tasks isolated).
8. **Knowledge Gap Task Isolation:** **PASS** (2,271 knowledge gap tasks isolated).
9. **JSONL Format Integrity:** **PASS** (0 malformed or truncated lines).
10. **Timestamp & Content Transformation Verification:** **PASS** (Zero regeneration or content transformation detected).

---

### 6. Contaminated Directory Status
- `longitudinal_data/v0.1.3-QA.1.1/`: **UNTOUCHED & QUARANTINED**.
- No overwriting, deletion, or merging was performed on the contaminated 561-patient sample directory.

---

### 7. Final Classification

```
AUTHORITATIVE_DATASET_RESTORED
```

The authoritative `v0.1.3-QA.1.1` release and its complete 1,140-patient source CSV population have been successfully restored to `longitudinal_data/authoritative/` with 100% byte-level integrity verified.
