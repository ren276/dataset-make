# PHC SaMD Experiment 001-QA2: SFT Baseline Plan

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Dataset Release:** `v0.1.3-QA.1.1` (**FROZEN**)  
**Model Target:** MedGemma 1.5 4B IT (`google/medgemma-1.5-4b-it`)  
**Revision:** `EXPERIMENT_001_QA2` (Reconciled derived contract after hardware OOM on initial BF16/4096 specification)  

---

## 1. Context & Reconciliation Rationale

The initial Experiment 001 contract specified full precision `bfloat16` base model with LoRA at `max_seq_length=4096`. During empirical training contract validation, this configuration triggered `CUDA out of memory` on the 15.56 GB RTX 4070 Ti SUPER GPU during backward pass (requiring ~17.2 GB VRAM).

To preserve the experimental integrity and baseline goal of testing record-grounded SFT on `v0.1.3-QA.1.1` without altering dataset records or adding auxiliary mechanisms (RAG, NLEM, clinical kernel), the contract is revised to **`EXPERIMENT_001_QA2`**:
* **Quantization:** QLoRA 4-bit NF4 (`load_in_4bit=True, bnb_4bit_quant_type='nf4'`)
* **Compute Dtype:** `bfloat16`
* **Sequence Length:** `max_seq_length=512` (Proven to cover 100.0% of all frozen dataset records with zero truncation and peak VRAM of 9.34 GB, leaving 6.22 GB of headroom).

---

## 2. Experimental Objectives

1. **Record Grounding:** Evaluate whether MedGemma 1.5 4B IT learns strict record-grounded retrieval, summarization, and explanation from synthetic PHC EHR records.
2. **Safe Abstention:** Assess refusal behavior on out-of-scope clinical queries (TF12) and missing data recognition (TF11).
3. **Clinical Normalization:** Evaluate entity normalization into standardized ICD-11 / SNOMED CT terminology (TF09).

---

## 3. Hardware & Memory Allocation

* **GPU Target:** 1× NVIDIA GeForce RTX 4070 Ti SUPER (15.56 GB VRAM)
* **Quantized Base Weights:** ~3.28 GB VRAM
* **LoRA Parameters ($r=16$):** ~0.11 GB VRAM
* **Measured Peak Memory at 512 Tokens:** **9.34 GB VRAM**
* **VRAM Safety Margin:** **6.22 GB VRAM headroom (40.0% margin)**

---

## 4. Frozen Dataset Integrity

* **Source Directory:** `longitudinal_data/v0.1.3-QA.1.1/`
* **Dataset Status:** Frozen & byte-for-byte immutable.
* **Train Records:** 1,915 tasks (798 patients)
* **Validation Records:** 328 tasks (114 patients)
* **Test Records:** 289 tasks (114 patients)
* **Safety Test Records:** 19,683 tasks (801 patients)
