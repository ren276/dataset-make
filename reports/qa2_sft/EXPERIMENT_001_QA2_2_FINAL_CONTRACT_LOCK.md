# PHC SaMD Experiment 001-QA2.2: Final Training Contract Lock Audit Report

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Authoritative Dataset Path:** `longitudinal_data/authoritative/v0.1.3-QA.1.1/` (**LOCKED & FROZEN**)  
**Quarantined Directory Path:** `longitudinal_data/v0.1.3-QA.1.1/` (**UNTOUCHED & FROZEN**)  
**Audit Purpose:** Final Technical Training Contract Lock Before Full SFT  
**Audit Timestamp:** 2026-08-12T12:00:36+05:30  

---

## 1. Executive Summary & Audit Decision

$$\mathbf{FINAL\ CLASSIFICATION:\ READY\_FOR\_EXPLICIT\_SFT\_APPROVAL}$$

$$\mathbf{CONTRACT\ STATUS:\ LOCKED\ (576\ TOKENS)}$$

$$\mathbf{FULL\ SFT\ STATUS:\ NOT\ STARTED\ (AWAITING\ HUMAN\ APPROVAL)}$$

### Key Contract Audit Highlights
1. **Authoritative Dataset SHA256 Checksums Re-verified:** All 6 dataset file checksums recalculated on the GPU host match the authoritative release **100% EXACTLY**.
2. **Dataset Path Lock:** `train.jsonl` (15,572 records) and `validation.jsonl` (2,229 records) are locked as the only SFT inputs. `tf12_safety_eval.jsonl` (2,051 records) and `knowledge_gap_tasks.jsonl` (2,271 records) are strictly isolated as evaluation-only pools and will **NOT** enter SFT.
3. **Explicit 576-Token Limitation Documented:** Across the 22,210 primary SFT records, exactly **44 records (0.20%)** exceed 576 tokens. Zero patient record context is lost, zero instructions are lost, 43 assistant target answers are truncated, and 44 EOS tokens are truncated. This is explicitly locked as a known Experiment 001 limitation (achieving **99.80% complete record coverage**).
4. **Assistant-Only Loss Masking:** Empirically verified on GPU (`system` and `user` prompt tokens masked to `-100`; `assistant` target tokens unmasked; metadata strictly excluded from model inputs).
5. **Worst-Case 576-Token Memory Check:** Validated on GPU via isolated 1-step forward/backward/optimizer step test:
   - **Forward Loss:** `0.2862` (Finite, `NaN/Inf = False`)
   - **LoRA Gradients:** Present & Non-Zero
   - **Base Model Gradients:** `0` (100% Base Model Parameters Frozen)
   - **Optimizer Step:** PASS (`AdamW`, `lr=2e-4`)
   - **Peak VRAM:** `13.10 GB` (with **2.46 GB / 15.8% VRAM headroom** on 15.56 GB RTX 4070 Ti SUPER with `expandable_segments:True`).

---

## 2. Six Authoritative Dataset SHA256 Checksum Table

| Dataset Input File | Expected Authoritative SHA256 | Recalculated GPU Host SHA256 | Record Count | Path Lock Status |
| :--- | :--- | :--- | :---: | :---: |
| `train.jsonl` | `8d8d6d9d8087c38c71d8bc4613e4cd64b8f8fa4fae021fb9309d1af553e2ce3f` | `8d8d6d9d8087c38c71d8bc4613e4cd64b8f8fa4fae021fb9309d1af553e2ce3f` | 15,572 | **LOCKED (SFT TRAIN)** |
| `validation.jsonl` | `34d221c5a045965a9335a7f68a0105ae232d577496f3224fc4bb6c89f93ad04a` | `34d221c5a045965a9335a7f68a0105ae232d577496f3224fc4bb6c89f93ad04a` | 2,229 | **LOCKED (SFT VAL)** |
| `test.jsonl` | `7d0ea53f5c820475d4e4d97e915f085381a8dfe39593bcf3b56a6c5043545da5` | `7d0ea53f5c820475d4e4d97e915f085381a8dfe39593bcf3b56a6c5043545da5` | 2,185 | **LOCKED (HELD-OUT TEST)** |
| `safety_test.jsonl` | `dba7e517fcc778c2b9113330a02f207604bfda6ce970d914bc70b11d8bf6617b` | `dba7e517fcc778c2b9113330a02f207604bfda6ce970d914bc70b11d8bf6617b` | 2,224 | **LOCKED (SAFETY TEST)** |
| `tf12_safety_eval.jsonl` | `fe542d48c8c739bfceb156abdfe151bfb1b1485e7d3fb60cb058df17de57e8fa` | `fe542d48c8c739bfceb156abdfe151bfb1b1485e7d3fb60cb058df17de57e8fa` | 2,051 | **EVALUATION ONLY (EXCLUDED FROM SFT)** |
| `knowledge_gap_tasks.jsonl` | `57809cf3c9131ad69a5412e33217cf4a733e5fc99b45c972b99777977954c509` | `57809cf3c9131ad69a5412e33217cf4a733e5fc99b45c972b99777977954c509` | 2,271 | **EVALUATION ONLY (EXCLUDED FROM SFT)** |

---

## 3. Final Locked Experiment 001-QA2 Runtime Hyperparameter Contract

```yaml
experiment_id: "EXPERIMENT_001_QA2"
model:
  name: "google/medgemma-1.5-4b-it"
  local_path: "/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it"
  revision: "91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b"

quantization:
  quant_type: "nf4"
  load_in_4bit: true
  double_quant: true
  compute_dtype: "bfloat16"

lora:
  r: 16
  alpha: 32
  dropout: 0.05
  bias: "none"
  task_type: "CAUSAL_LM"
  target_modules:
    - "q_proj"
    - "k_proj"
    - "v_proj"
    - "o_proj"
    - "gate_proj"
    - "up_proj"
    - "down_proj"

training:
  max_length: 576
  per_device_train_batch_size: 1
  gradient_accumulation_steps: 16
  effective_batch_size: 16
  optimizer: "adamw_torch"
  learning_rate: 0.0002
  lr_scheduler_type: "cosine"
  warmup_ratio: 0.03
  num_train_epochs: 3
  seed: 42
  gradient_checkpointing: true
  use_reentrant: false
  assistant_only_loss: true
  cuda_alloc_conf: "expandable_segments:True"

hardware_validation:
  gpu: "NVIDIA GeForce RTX 4070 Ti SUPER (15.56 GB VRAM)"
  peak_allocated_vram: "13.10 GB"
  peak_reserved_vram: "13.64 GB"
  vram_headroom: "2.46 GB (15.8%)"
```

---

## 4. Strict Compliance & Immutability Confirmation

1. **Dataset Unmodified:** `longitudinal_data/authoritative/v0.1.3-QA.1.1/` remains 100% frozen and byte-identical.
2. **Quarantine Preserved:** `longitudinal_data/v0.1.3-QA.1.1/` remains untouched as forensic evidence.
3. **Hard Stop Enforced:** Full 3-epoch SFT has **NOT** been started. The contract is locked and ready for explicit human approval.
