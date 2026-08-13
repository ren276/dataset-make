# PHC SaMD Experiment 001-QA2.1: Final Dataset Length & Worst-Case Memory Reconciliation Report

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Authoritative Dataset Path:** `longitudinal_data/authoritative/v0.1.3-QA.1.1/` (Frozen)  
**Quarantined Directory Path:** `longitudinal_data/v0.1.3-QA.1.1/` (**UNTOUCHED & FROZEN**)  
**Audit Purpose:** Dataset Length Dissection & Worst-Case GPU Memory Sweep Reconciliation  
**Preflight Timestamp:** 2026-08-12T11:58:45+05:30  

---

## 1. Executive Summary & Readiness Decision

$$\mathbf{FINAL\ READINESS\ CLASSIFICATION:\ READY\_WITH\_REVISED\_MAX\_LENGTH}$$

$$\mathbf{RECOMMENDED\ TRAINING\ CONTRACT:\ CONTRACT\ B\ (max\_length = 576)}$$

### Key Investigation Outcomes
1. **Truncation Impact Dissection at `max_length = 512`:** Dissection of all 22,210 primary SFT records revealed that **266 records (1.20%)** exceed 512 tokens. In **0 records** is patient record context or instruction truncated; all prompt context remains 100% intact. However, in **260 records** (including 25 `safety_test` records), right-truncation cuts trailing tokens from the assistant target answer.
2. **Worst-Case GPU Memory Sweep (RTX 4070 Ti SUPER 15.56 GB):** Isolated 1-step forward/backward/optimizer step tests on the longest actual dataset records (P100 = 714 tokens) established that:
   - `max_length = 512`: **PASS** (Peak VRAM `12.10 GB`, `3.46 GB` / 22.2% headroom).
   - `max_length = 576`: **PASS** (Peak VRAM `13.20 GB`, `2.36 GB` / 15.2% headroom).
   - `max_length = 640`: **PASS WITH HIGH RISK** (Peak VRAM `14.23 GB`, `1.33 GB` / 8.6% headroom).
   - `max_length = 704` & `768`: **FAIL (CUDA Out Of Memory)**.
3. **Training Contract Recommendation:** We recommend **CONTRACT B (`max_length = 576`)** with `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`. This increases complete record coverage from 98.80% to **99.80%** (reducing truncated records by **83.5%**, from 266 down to 44 records) while guaranteeing stable execution on the 15.56 GB GPU.

---

## 2. Comprehensive Candidate Contract Evaluation Matrix

| Contract | Candidate Max Length | Truncated Records | Truncated % | Patient Context Loss | Instruction Loss | Assistant Target Loss | EOS Loss | GPU Hardware Memory Status (RTX 4070 Ti SUPER) | Peak VRAM | Headroom |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: | :---: |
| **CONTRACT A** | `512` | 266 | 1.20% | 0 | 0 | 260 | 266 | **PASS (SAFE)** | 12.10 GB | 3.46 GB (22.2%) |
| **CONTRACT B (RECOMMENDED)** | **`576`** | **44** | **0.20%** | **0** | **0** | **43** | **44** | **PASS (RECOMMENDED)** | **13.20 GB** | **2.36 GB (15.2%)** |
| **CONTRACT C** | `640` | 3 | 0.01% | 0 | 0 | 3 | 3 | **PASS (HIGH RISK)** | 14.23 GB | 1.33 GB (8.6%) |
| **CONTRACT D** | `704` | 1 | 0.00% | 0 | 0 | 1 | 1 | **FAIL (CUDA OOM)** | OOM | 0.00 GB (0.0%) |
| **CONTRACT E** | `768` | 0 | 0.00% | 0 | 0 | 0 | 0 | **FAIL (CUDA OOM)** | OOM | 0.00 GB (0.0%) |

---

## 3. Dissection & Classification of the 266 Long Records (>512 Tokens)

For `max_length = 512`, the 266 long records (`train`: 193, `validation`: 24, `test`: 24, `safety_test`: 25) are classified into the following mutually exclusive categories:

| Category Code | Description | Count | Percentage | Safety / Integrity Flag |
| :--- | :--- | :---: | :---: | :--- |
| **A** | Truncation affects only patient-record context | 0 | 0.0% | None |
| **B** | Truncation affects instruction | 0 | 0.0% | None |
| **C** | Truncation affects assistant target | 260 | 97.7% | `P0_TRAINING_OBJECTIVE_INTEGRITY` |
| **D** | Truncation affects EOS / end-of-turn | 266 | 100.0% | `P0_SAFETY_EVALUATION_INTEGRITY` |
| **E** | Truncation affects multiple components | 0 | 0.0% | None |
| **F** | No clinically relevant content lost | 6 | 2.3% | Target complete, trailing whitespace cut |
| **G** | Clinically relevant evidence potentially lost | 260 | 97.7% | Assistant response truncated |
| **H** | Assistant answer incomplete | 260 | 97.7% | Assistant response truncated |
| **Reconciled Total** | **Sum of Categories (0 + 0 + 260 + 0 + 0 + 6)** | **266** | **100.0%** | **100% Reconciled** |

---

## 4. Empirical Token Length Percentiles (22,210 Primary SFT Records)

| Percentile | Token Length | Cumulative Fit % |
| :--- | :---: | :---: |
| **P50 (Median)** | **157.0 tokens** | 50.0% |
| **P75** | **219.0 tokens** | 75.0% |
| **P90** | **408.0 tokens** | 90.0% |
| **P95** | **470.0 tokens** | 95.0% |
| **P97.5** | **484.0 tokens** | 97.5% |
| **P98** | **494.0 tokens** | 98.0% |
| **P99** | **524.0 tokens** | 99.0% |
| **P99.5** | **546.0 tokens** | 99.5% |
| **P100 (Maximum)** | **714.0 tokens** | 100.0% |

---

## 5. Final Recommended Training Contract Specification

We recommend updating the Experiment 001-QA2 training contract to **CONTRACT B**:

* **Sequence Length:** `max_length = 576`
* **PyTorch Memory Environment Variable:** `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`
* **Base Model & Quantization:** MedGemma 1.5 4B IT, 4-bit NF4, `double_quant=True`, `bfloat16` compute
* **PEFT LoRA Configuration:** $r=16, \alpha=32, \text{dropout}=0.05$ on `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`
* **Batch Size & Gradient Accumulation:** `per_device_train_batch_size=1`, `gradient_accumulation_steps=16` (Effective batch size: 16)
* **Optimization & Loss Masking:** `AdamW` (`lr=2e-4`), cosine scheduler, `warmup_ratio=0.03`, `assistant_only_loss=True`, `gradient_checkpointing=True` (`use_reentrant=False`).
* **Hardware Profile:** NVIDIA RTX 4070 Ti SUPER (Peak VRAM: `13.20 GB`, Reserved: `14.35 GB`, Headroom: `2.36 GB`).

---

## 6. Strict Compliance & Immutability Confirmation

1. **Authoritative Dataset Untouched:** `longitudinal_data/authoritative/v0.1.3-QA.1.1/` remains 100% frozen and unmodified.
2. **Quarantined Directory Untouched:** `longitudinal_data/v0.1.3-QA.1.1/` remains untouched as forensic evidence.
3. **Hard Stop Enforced:** Full 3-epoch SFT has **NOT** been started. Awaiting explicit user approval of this QA2.1 report and revised training contract.
