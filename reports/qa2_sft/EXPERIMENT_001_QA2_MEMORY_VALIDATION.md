# PHC SaMD Experiment 001-QA2: Memory Validation Report

**Label:** `ENVIRONMENT_VALIDATION_ONLY`  
**Target Hardware:** NVIDIA GeForce RTX 4070 Ti SUPER (15.56 GB Total VRAM)  
**Quantization Scheme:** QLoRA 4-bit NF4 (`bnb_4bit_quant_type='nf4'`, `bnb_4bit_use_double_quant=True`)  
**Compute Dtype:** `bfloat16`  
**Optimizer:** `AdamW` (state instantiated, 1 forward + 1 backward + 1 step executed)  

---

## 1. Empirical Sequence Length Memory Sweep Results

Each sequence length candidate was evaluated in an isolated Python process executing a full forward pass, loss calculation, backward pass, and optimizer step under `gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})`.

| Candidate SeqLen | Run 1 Peak VRAM | Run 2 Peak VRAM | Allocated VRAM | Reserved VRAM | OOM Status | Reproducibility Status | VRAM Safety Headroom |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **512 tokens** | **9.34 GB** | **9.34 GB** | **4.05 GB** | **10.55 GB** | **PASS (NO OOM)** | **100% Identical** | **6.22 GB (40.0% Margin)** |
| **1024 tokens** | OOM | OOM | 14.55 GB | 14.90 GB | **FAILED (OOM)** | Failed in backward | -0.34 GB |
| **1536 tokens** | OOM | OOM | 14.62 GB | 14.92 GB | **FAILED (OOM)** | Failed in backward | -0.36 GB |
| **2048 tokens** | OOM | OOM | 14.88 GB | 14.95 GB | **FAILED (OOM)** | Failed in backward | -0.39 GB |

---

## 2. Technical Findings & Selection Rationale

1. **Why `max_seq_length=512` is Selected:**
   * It is the highest sequence length candidate that successfully executes full forward and backward passes without triggering memory allocation failure on 15.56 GB VRAM.
   * It leaves **6.22 GB of unallocated VRAM headroom**, avoiding emergency CUDA memory fragmentation or fallback.
   * Peak memory behavior is 100% reproducible across consecutive validation runs (9.34 GB in both Run 1 and Run 2).

2. **Dataset Alignment:**
   * Re-computing the exact token length distribution across all 22,215 records in `v0.1.3-QA.1.1` revealed that **100.0% of records fit within 512 tokens** (P100 max record length is 489 tokens).
   * Zero records exceed 512 tokens, meaning `max_seq_length=512` causes **0.00% dataset truncation**.
