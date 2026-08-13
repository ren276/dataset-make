# Experiment 001 Plan: First Record-Grounded SLM Research Baseline

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Dataset Release:** `v0.1.3-QA.1.1` (FROZEN)  
**Target Model:** MedGemma 1.5 4B IT (`google/medgemma-1.5-4b-it`)  
**Experiment Type:** Controlled Supervised Fine-Tuning (SFT) Baseline  
**Status:** Pre-Training Audit & Environment Preflight Phase  

---

## 1. Experiment Objective

The primary objective of Experiment 001 is to establish a rigorous, controlled **RESEARCH BASELINE** by evaluating the hypothesis:

> *"Can the selected SLM learn record-grounded retrieval, explanation, summarization, normalization, missing-information recognition, and safe-abstention behavior from the deterministic synthetic PHC dataset without learning unsupported clinical inference or prescribing behavior?"*

### Explicit Disclaimer & Scope
- **RESEARCH BASELINE ONLY:** This experiment serves purely as an empirical baseline to measure dataset alignment and safety boundaries.
- **NOT A CLINICAL VALIDATION STUDY:** This does not demonstrate clinical efficacy or medical safety in real-world practice.
- **NOT A PRODUCTION QUALIFICATION:** This model artifact will not be deployed for direct patient care or clinical decision-making.

---

## 2. Model Environment & Technical Audit

| Property | Environment Specification / Audit Result |
| :--- | :--- |
| **Model Identifier** | `google/medgemma-1.5-4b-it` |
| **Local Model Path** | `/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it` |
| **Model Revision** | Local commit `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b` |
| **Architecture** | `Gemma3ForConditionalGeneration` (Text: `gemma3_text`, Vision: `siglip_vision_model`) |
| **Parameter Count** | 4.3 Billion total parameters (Text model: 34 layers, `hidden_size`: 2560, `intermediate_size`: 10240, 8 attention heads, 4 KV heads) |
| **Supported Context Length**| 131,072 tokens (128k context support with 1024 sliding window every 6 layers) |
| **Native Precision (dtype)**| `bfloat16` |
| **Quantization Status** | Unquantized (`safetensors` format) |
| **GPU Hardware** | 1× NVIDIA GeForce RTX 4070 Ti SUPER |
| **GPU VRAM** | 15.56 GB VRAM |
| **CUDA Version** | CUDA 13.0 (Driver version: 13.3) |
| **PyTorch Version** | `2.13.0+cu130` |
| **Transformers Version** | `5.15.0` |
| **PEFT Status** | **MISSING** (Not installed in active Conda environment) |
| **TRL Status** | **MISSING** (Not installed in active Conda environment) |
| **bitsandbytes Status** | **MISSING** (Not installed in active Conda environment) |
| **Python Version** | `3.11.15` |

---

## 3. Training Architecture & Isolation Discipline

Experiment 001 strictly isolates the Supervised Fine-Tuning (SFT) effect of dataset `v0.1.3-QA.1.1`.

### Strictly Prohibited Components (No Single-Variable Contamination)
To ensure clean ablation discipline, the following components are **EXCLUDED** from Experiment 001:
- ❌ **No RAG (Retrieval-Augmented Generation)**
- ❌ **No NLEM Retrieval at Inference Time**
- ❌ **No Vector Databases / ChromaDB**
- ❌ **No Clinical Execution Kernel**
- ❌ **No Physician Simulation Layer**
- ❌ **No External Clinical Knowledge Injection**
- ❌ **No Teacher-Generated Targets**
- ❌ **No Synthetic Data Augmentation Post-Release**

---

## 4. Dataset Splits & Isolation Guarantees

The experiment utilizes the frozen dataset `v0.1.3-QA.1.1` under `longitudinal_data/v0.1.3-QA.1.1/`.

| Split File | Patient Count | Task Count | Purpose / Isolation Rule |
| :--- | :---: | :---: | :--- |
| `train.jsonl` | 798 | 15,572 | Primary SFT Training Set |
| `validation.jsonl` | 114 | 2,229 | Hyperparameter Tuning & Validation |
| `test.jsonl` | 114 | 2,185 | Held-out SFT Primary Benchmark |
| `safety_test.jsonl` | 114 | 2,224 | Held-out SFT Safety Benchmark |
| **Total Primary SFT Pool** | **1,140** | **22,210** | **Strict Patient-Level Isolation Maintained** |
| `tf12_safety_eval.jsonl` | Held-out | 2,051 | **EVALUATION ONLY** (MUST NOT enter SFT) |
| `knowledge_gap_tasks.jsonl` | Held-out | 2,271 | **EVALUATION ONLY** (MUST NOT enter SFT) |

> [!IMPORTANT]
> - Patient-level isolation is strictly enforced across splits. No patient overlap exists between `train`, `validation`, `test`, and `safety_test`.
> - The SFT pool includes only **396 representative TF12 safety-baseline examples**.
> - The isolated **2,051 TF12 safety eval tasks** and **2,271 knowledge-gap tasks** MUST NEVER enter the SFT training set.

---

## 5. Task Scope & Critical Safety Boundaries

### Included SFT Tasks (11 Task Families)
1. **TF01:** Historical EHR Retrieval
2. **TF02:** Consultation Summarization
3. **TF03:** Encounter / Referral Summary
4. **TF04:** Prescription Record Explanation
5. **TF05:** Record-Grounded Medication Interpretation
6. **TF07:** Observation / Vital Explanation
7. **TF08:** Historical Patient Explanation
8. **TF09:** Clinical Normalization
9. **TF10-A:** Objective Record Discordance Recognition
10. **TF11:** Missing Information Recognition
11. **TF12:** Safe Abstention Baseline (396 representative tasks)

### Explicitly Excluded Tasks from SFT
- **TF05-K:** Pharmacology Knowledge Interpretation (Authoritative NLEM missing)
- **TF06:** Complex Clinical Inference / Decision Support (No authoritative source)
- **TF10-B:** Diagnostic / Therapeutic Conflict Resolution (No authoritative source)

### Critical Safety Boundary
The model MUST NOT be trained or permitted to exhibit any of the following autonomous physician behaviors:
- Prescribing medications or altering therapy
- Selecting drug treatments or dosages
- Inventing unrecorded diagnoses, symptoms, or patient outcomes
- Inferring contraindications from unsupplied medical knowledge
- Claiming NLEM membership without explicit NLEM evidence in record
- Converting IPHS facility standards into patient-specific treatment authorizations

---

## 6. Model-Facing Format Specification

The model-facing JSONL format strictly adheres to the standard `system` / `user` / `assistant` turn semantics.

### Prompt Template Structure
```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a clinical record explanation assistant.\nUse only the information provided.\nDo not invent clinical facts.\nDo not prescribe.\nIf required information is absent, state that it is not recorded."
    },
    {
      "role": "user",
      "content": "PATIENT RECORD:\n[Longitudinal EHR Context]\n\nINSTRUCTION:\n[Task Query]"
    },
    {
      "role": "assistant",
      "content": "[Target Grounded Response]"
    }
  ]
}
```

- **Zero Internal Metadata:** No internal fields (`example_id`, `patient_id`, `task_family`, `evidence_mode`, etc.) are exposed in model input messages. Provenance metadata is stored separately in `sft_metadata.jsonl`.
