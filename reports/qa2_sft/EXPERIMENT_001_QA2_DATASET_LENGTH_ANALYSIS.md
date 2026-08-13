# PHC SaMD Experiment 001-QA2: Dataset Token-Length Distribution Analysis

**Dataset Release:** `v0.1.3-QA.1.1` (**FROZEN**)  
**Tokenizer:** `GemmaTokenizer` (`google/medgemma-1.5-4b-it`)  
**Chat Template:** MedGemma 1.5 4B IT Native Jinja2 Chat Template  
**Total Records Analyzed:** 22,215 records (`train.jsonl`, `validation.jsonl`, `test.jsonl`, `safety_test.jsonl`)  

---

## 1. Token Length Percentiles (Measured from Frozen Dataset)

| Percentile Metric | Exact Token Count |
| :--- | :---: |
| **P50 (Median)** | **422.0 tokens** |
| **P75** | **430.0 tokens** |
| **P90** | **438.0 tokens** |
| **P95** | **443.0 tokens** |
| **P97.5** | **447.0 tokens** |
| **P98** | **449.0 tokens** |
| **P98.4** | **450.0 tokens** |
| **P99** | **453.0 tokens** |
| **P99.5** | **457.0 tokens** |
| **P100 (Maximum Dataset Length)** | **489.0 tokens** |

---

## 2. Exceedance Analysis by Sequence Threshold

| Sequence Threshold | Record Count Exceeding Threshold | Exceedance Percentage | Truncation Impact |
| :---: | :---: | :---: | :--- |
| **> 512 tokens** | **0 records** | **0.00%** | **ZERO TRUNCATION (100.0% Coverage)** |
| **> 1024 tokens** | **0 records** | **0.00%** | Zero Truncation |
| **> 1536 tokens** | **0 records** | **0.00%** | Zero Truncation |
| **> 2048 tokens** | **0 records** | **0.00%** | Zero Truncation |

---

## 3. Truncation Audit Finding

* **Audit Conclusion:** Because the maximum record length across the entire frozen release is 489 tokens, setting `max_length=512` guarantees that **0 records are truncated**.
* **Clinical Integrity:** No system instructions, patient contexts, historical encounter facts, instructions, or target assistant responses are modified or removed during training.
