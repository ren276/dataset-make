# PHC SaMD Experiment 001-QA2: Final Training Preflight Report

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Authoritative Release Path:** `longitudinal_data/authoritative/v0.1.3-QA.1.1/`  
**Quarantined Directory Path:** `longitudinal_data/v0.1.3-QA.1.1/` (**UNTOUCHED & FROZEN**)  
**Audit Purpose:** Final Technical Training Preflight Before Full SFT  
**Preflight Timestamp:** 2026-08-12T11:55:40+05:30  

---

## 1. Executive Summary & Readiness Decision

$$\mathbf{FINAL\ READINESS\ CLASSIFICATION:\ READY\_FOR\_FULL\_SFT}$$

### Key Verification Milestones Passed (26/26 Checks Verified)
1. **Authoritative Dataset SHA256 Checksums:** All 6 SHA256 checksums recalculated on this GPU host match the original-machine authoritative hashes **100% EXACTLY**.
2. **Physical Record Counts:** Primary SFT records total **22,210** (`train`: 15,572, `validation`: 2,229, `test`: 2,185, `safety_test`: 2,224). Isolated evaluation pools total **4,322** (`tf12_safety_eval`: 2,051, `knowledge_gap_tasks`: 2,271).
3. **Patient Population & Split Isolation:** Primary SFT split population is **1,140 patients** (`train`: 798, `val`: 114, `test`: 114, `safety`: 114). Patient leakage across all primary splits and evaluation pools is **0 (100% Isolated)**.
4. **Example ID Uniqueness:** 26,532 total unique IDs across all pools with **0 collisions (100% Unique)**.
5. **Model Identity:** MedGemma 1.5 4B IT model verified at `/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it` (Revision: `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b`).
6. **Package Environment:** Python 3.11.15, PyTorch 2.13.0+cu130, Transformers 5.15.0, Accelerate 1.14.0, Datasets 5.0.1, PEFT 0.20.0, TRL 1.9.2, bitsandbytes 0.50.0, CUDA 13.0.
7. **QLoRA Parameter Freeze:** Base model parameters are 100% frozen (`0` base parameters require grad). LoRA adapter ($r=16, \alpha=32$) adds **32,788,480 trainable parameters (1.2996%)** across `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`.
8. **Loss Masking Verification:** Assistant-only loss masking verified (`system` and `user` prompt tokens masked to `-100`; `assistant` response tokens unmasked).
9. **Controlled 1-Step Training Validation:** Executed 1 forward pass, 1 backward pass, and 1 `AdamW` optimizer step on GPU:
   - **Forward Loss:** `0.8489` (Finite, `NaN/Inf = False`)
   - **LoRA Gradients:** Present & Non-Zero
   - **Optimizer Step:** PASS
   - **Peak VRAM:** `6.44 GB` (with **9.12 GB VRAM headroom** on 15.56 GB RTX 4070 Ti SUPER).

---

## 2. Six SHA256 Checksum Verification Table

| File Path | Expected Authoritative SHA256 | Recalculated GPU Host SHA256 | Record Count | Verification Status |
| :--- | :--- | :--- | :---: | :---: |
| `train.jsonl` | `8d8d6d9d8087c38c71d8bc4613e4cd64b8f8fa4fae021fb9309d1af553e2ce3f` | `8d8d6d9d8087c38c71d8bc4613e4cd64b8f8fa4fae021fb9309d1af553e2ce3f` | 15,572 | **PASS (EXACT)** |
| `validation.jsonl` | `34d221c5a045965a9335a7f68a0105ae232d577496f3224fc4bb6c89f93ad04a` | `34d221c5a045965a9335a7f68a0105ae232d577496f3224fc4bb6c89f93ad04a` | 2,229 | **PASS (EXACT)** |
| `test.jsonl` | `7d0ea53f5c820475d4e4d97e915f085381a8dfe39593bcf3b56a6c5043545da5` | `7d0ea53f5c820475d4e4d97e915f085381a8dfe39593bcf3b56a6c5043545da5` | 2,185 | **PASS (EXACT)** |
| `safety_test.jsonl` | `dba7e517fcc778c2b9113330a02f207604bfda6ce970d914bc70b11d8bf6617b` | `dba7e517fcc778c2b9113330a02f207604bfda6ce970d914bc70b11d8bf6617b` | 2,224 | **PASS (EXACT)** |
| `tf12_safety_eval.jsonl` | `fe542d48c8c739bfceb156abdfe151bfb1b1485e7d3fb60cb058df17de57e8fa` | `fe542d48c8c739bfceb156abdfe151bfb1b1485e7d3fb60cb058df17de57e8fa` | 2,051 | **PASS (EXACT)** |
| `knowledge_gap_tasks.jsonl` | `57809cf3c9131ad69a5412e33217cf4a733e5fc99b45c972b99777977954c509` | `57809cf3c9131ad69a5412e33217cf4a733e5fc99b45c972b99777977954c509` | 2,271 | **PASS (EXACT)** |

---

## 3. Dataset Tokenization Percentiles (22,210 Primary Records)

Tokenization performed using the exact local `MedGemma` tokenizer and native chat template:

| Percentile | Token Length | Status |
| :--- | :---: | :---: |
| **P50 (Median)** | **157.0 tokens** | Within 512 |
| **P75** | **219.0 tokens** | Within 512 |
| **P90** | **408.0 tokens** | Within 512 |
| **P95** | **470.0 tokens** | Within 512 |
| **P97.5** | **484.0 tokens** | Within 512 |
| **P98** | **494.0 tokens** | Within 512 |
| **P99** | **524.0 tokens** | Truncated to 512 |
| **P99.5** | **546.0 tokens** | Truncated to 512 |
| **P100 (Maximum)** | **714.0 tokens** | Truncated to 512 |

* **Records $\le 512$ tokens:** 21,944 (98.80%)
* **Records > 512 tokens:** 266 (1.20%)
* **Sequence Truncation:** Enabled at `max_length=512`.

---

## 4. Controlled 1-Step Training & Memory Profile

| Preflight Parameter / Metric | Measured Value | Standard / Expectation | Preflight Pass Status |
| :--- | :--- | :--- | :---: |
| **Quantization Scheme** | 4-bit NF4 (`double_quant=True`, `bf16` compute) | 4-bit NF4 | **PASS** |
| **LoRA Target Modules** | `q, k, v, o, gate, up, down_proj` | `q, k, v, o, gate, up, down_proj` | **PASS** |
| **Trainable Parameters** | 32,788,480 (1.2996%) | ~32.7M | **PASS** |
| **Base Model Freeze** | 0 Base Parameters with `requires_grad=True` | 0 Base Parameters | **PASS** |
| **Assistant-Only Loss Masking** | System/User = `-100`, Assistant = Unmasked | Prompt Masked | **PASS** |
| **Forward Pass Loss** | `0.8489` | Finite Loss | **PASS** |
| **NaN / Inf Check** | `False` | No NaN/Inf | **PASS** |
| **LoRA Gradient Status** | Present & Non-Zero | Valid Gradients | **PASS** |
| **Optimizer Step** | Successful (`AdamW`, `lr=2e-4`) | Step Success | **PASS** |
| **Allocated VRAM** | `4.92 GB` | $< 15.56\text{ GB}$ | **PASS** |
| **Reserved VRAM** | `7.01 GB` | $< 15.56\text{ GB}$ | **PASS** |
| **Peak VRAM** | `6.44 GB` | $< 15.56\text{ GB}$ | **PASS** |
| **VRAM Safety Headroom** | **9.12 GB (58.6% Headroom)** | $> 20\%$ Headroom | **PASS** |

---

## 5. Strict Compliance & Immutability Confirmation

1. **Dataset Path Enforced:** Full SFT will read strictly from `longitudinal_data/authoritative/v0.1.3-QA.1.1/`.
2. **Quarantine Preserved:** The directory `longitudinal_data/v0.1.3-QA.1.1/` remains untouched as forensic evidence.
3. **Safety Pool Isolation:** `tf12_safety_eval.jsonl` (2,051 records) and `knowledge_gap_tasks.jsonl` (2,271 records) are strictly excluded from SFT.
4. **Final Stop Enforced:** Full SFT has **NOT** been started in this preflight task. Awaiting explicit user approval to launch the 3-epoch SFT run.
