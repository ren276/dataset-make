# PHC SaMD Experiment 001-QA2: SFT Training Completion Report

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Authoritative Dataset Path:** `longitudinal_data/authoritative/v0.1.3-QA.1.1/` (**FROZEN & UNTOUCHED**)  
**Quarantined Directory Path:** `longitudinal_data/v0.1.3-QA.1.1/` (**UNTOUCHED & FROZEN**)  
**Base Model:** MedGemma 1.5 4B IT (`/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it`)  
**Model Revision:** `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b`  
**Training Status:** **COMPLETED SUCCESSFULLY (3.0 / 3 Epochs Finished)**  
**Completion Timestamp:** 2026-08-12T16:31:37+05:30  

---

## 1. Executive Summary & Verification Checklist

$$\mathbf{SFT\ EXPERIMENT\ STATUS:\ COMPLETED\ SUCCESSFULLY}$$

$$\mathbf{TOTAL\ OPTIMIZER\ STEPS:\ 2,922\ /\ 2,922\ (100\%\ COMPLETE)}$$

$$\mathbf{FINAL\ EVALUATION\ LOSS:\ 0.001366}$$

### 14-Point Pre- and Post-Training Verification Checklist
1. **Dataset SHA256 Verification:** Pre-training check verified TRAIN (`8d8d6d9...`) and VAL (`34d221c...`) SHA256 hashes **100% MATCHED**.
2. **Dataset Immutability:** Authoritative dataset `longitudinal_data/authoritative/v0.1.3-QA.1.1/` remained 100% frozen (**0 modifications**).
3. **Quarantined Evidence:** Quarantined directory `longitudinal_data/v0.1.3-QA.1.1/` remained **UNTOUCHED**.
4. **Evaluation Isolation:** `tf12_safety_eval.jsonl`, `knowledge_gap_tasks.jsonl`, `test.jsonl`, and `safety_test.jsonl` were strictly excluded from gradient updates.
5. **Model Identity:** MedGemma 1.5 4B IT model revision `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b` used exclusively.
6. **QLoRA Quantization:** 4-bit NF4 quantization (`double_quant=True`, `bfloat16` compute). Base model weights 100% frozen.
7. **LoRA Adapter:** $r=16, \alpha=32, \text{dropout}=0.05$ on all 7 target projection modules (`q, k, v, o, gate, up, down_proj`). Trainable parameters: **32,788,480 (0.7567%)**.
8. **Locked Sequence Length:** `max_length = 576` enforced (`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`).
9. **Batch Size & Accumulation:** `per_device_train_batch_size=1`, `gradient_accumulation_steps=16` (Effective Batch Size = 16).
10. **Optimizer & Schedule:** `AdamW` (`lr=2e-4`), cosine scheduler (`warmup_steps=87`), seed = 42.
11. **Loss Masking:** Assistant-only loss masking verified (`system` and `user` prompt tokens masked to `-100`; `assistant` target tokens unmasked). Internal metadata strictly excluded from model inputs.
12. **Peak GPU Memory:** Maximum allocated VRAM was **7.94 GB** on NVIDIA RTX 4070 Ti SUPER (15.56 GB total), leaving **7.62 GB VRAM safety headroom (49.0% headroom)** throughout all 3 epochs.
13. **Zero CUDA OOM / Zero NaN/Inf:** 0 CUDA OOM errors and 0 NaN/Inf loss values occurred across all 2,922 steps.
14. **Checkpoints & Adapter Saved:** All 3 epoch checkpoints (`checkpoint-974`, `checkpoint-1948`, `checkpoint-2922`) and the final standalone LoRA adapter (`final_adapter`) were saved cleanly to disk.

---

## 2. Training & Validation Loss Trajectory

| Epoch | Optimizer Step | Train Loss (Sampled Step) | Validation Loss (End of Epoch) | Learning Rate | GPU Peak VRAM |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Start** | Step 10 | `2.5312` | - | `2.298e-5` | 6.44 GB |
| **Epoch 1** | Step 974 | `0.000318` | **`0.003932`** | `1.503e-4` | 7.82 GB |
| **Epoch 2** | Step 1948 | `0.000042` | **`0.001648`** | `5.008e-5` | 7.91 GB |
| **Epoch 3 (Final)** | **Step 2922** | **`0.0000026`** | **`0.001366`** | **`0.000e+0`** | **7.94 GB** |

---

## 3. Post-Training Artifact Inventory

All experimental artifacts have been saved under the dedicated Experiment 001 output directory:

* **Final Saved LoRA Adapter Directory:** [/media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/final_adapter](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/final_adapter)
  * `adapter_model.safetensors` (131.25 MB)
  * `adapter_config.json`
  * `tokenizer.json` & `tokenizer_config.json`
  * `chat_template.jinja`
* **Epoch Checkpoints:**
  * Epoch 1: [/media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/checkpoint-974](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/checkpoint-974)
  * Epoch 2: [/media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/checkpoint-1948](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/checkpoint-1948)
  * Epoch 3: [/media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/checkpoint-2922](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/checkpoint-2922)
* **Machine-Readable Audit File:** [EXPERIMENT_001_QA2_TRAINING_COMPLETION.json](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/EXPERIMENT_001_QA2_TRAINING_COMPLETION.json)
* **Markdown Completion Document:** [EXPERIMENT_001_QA2_TRAINING_COMPLETION.md](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/EXPERIMENT_001_QA2_TRAINING_COMPLETION.md)

---

## 4. Final Post-Training Compliance Statement

1. **Frozen Dataset Unmodified:** `longitudinal_data/authoritative/v0.1.3-QA.1.1/` remains 100% frozen and byte-identical.
2. **Quarantined Evidence Preserved:** `longitudinal_data/v0.1.3-QA.1.1/` remains untouched as forensic evidence.
3. **No Premature Evaluation:** Held-out test sets (`test.jsonl` and `safety_test.jsonl`) remain completely untouched. Post-training evaluation will proceed only upon explicit instructions.
