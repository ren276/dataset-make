# PHC SaMD Experiment 001-QA2: Formal Training Contract

**Revision:** `EXPERIMENT_001_QA2`  
**Previous Revision:** `EXPERIMENT_001_PRETRAINING_CONTRACT: FAILED_HARDWARE_COMPATIBILITY`  
**Dataset:** `longitudinal_data/v0.1.3-QA.1.1/` (**FROZEN**)  
**Model Target:** MedGemma 1.5 4B IT (`google/medgemma-1.5-4b-it`)  
**Hardware Target:** 1× NVIDIA GeForce RTX 4070 Ti SUPER (15.56 GB VRAM)  

---

## 1. Formal Specification Clause

The training configuration for Experiment 001 is formally bound to **`EXPERIMENT_001_QA2`**:

```yaml
experiment_id: "EXPERIMENT_001_QA2"
model:
  path: "/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it"
  hub_id: "google/medgemma-1.5-4b-it"
  revision: "91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b"
quantization:
  scheme: "QLoRA 4-bit NF4"
  bnb_4bit_quant_type: "nf4"
  bnb_4bit_use_double_quant: true
  bnb_4bit_compute_dtype: "bfloat16"
peft:
  type: "LORA"
  r: 16
  alpha: 32
  dropout: 0.05
  target_modules: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
hyperparameters:
  max_length: 512
  per_device_train_batch_size: 1
  gradient_accumulation_steps: 16
  effective_batch_size: 16
  learning_rate: 0.0002
  lr_scheduler_type: "cosine"
  warmup_ratio: 0.03
  num_train_epochs: 3
  seed: 42
  assistant_only_loss: true
  gradient_checkpointing: true
```

---

## 2. Parameter Scope & Quantization Audit

* **Total Model Parameters:** 2,523,011,440
* **Trainable Parameters:** 32,788,480
* **Trainable Parameter Ratio:** **1.300%**
* **Base Model Status:** 4-bit NF4 quantized base weights frozen (`requires_grad=False`).
* **Trainable Adapter Status:** LoRA linear adapters (`q, k, v, o, gate, up, down_proj`) active (`requires_grad=True`).

---

## 3. Loss Masking Verification

* **System Prompt Tokens:** Masked (`labels == -100`)
* **User Record Tokens:** Masked (`labels == -100`)
* **Assistant Target Response Tokens:** Active loss (`labels != -100`)
* **EOS Turn Marker (`<end_of_turn>\n`):** Active loss (`labels != -100`)
* **Metadata Fields:** Zero metadata fields present in `input_ids` or `labels`.
