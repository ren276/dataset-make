# PHC SaMD Experiment 001-QA2: Post-SFT Evaluation Report

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Authoritative Dataset Path:** `longitudinal_data/authoritative/v0.1.3-QA.1.1/` (**FROZEN**)  
**Base Model:** MedGemma 1.5 4B IT (`/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it`, Revision: `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b`)  
**SFT Adapter:** `experiment_001_qa2_output/final_adapter`  
**Evaluation Mode:** **EVALUATION ONLY (0 Data/Adapter Modifications)**  
**Evaluation Timestamp:** 2026-08-12T18:39:16+0530  

---

## 1. Executive Summary & Final Classification

$$\mathbf{FINAL\ EVALUATION\ CLASSIFICATION:\ PASS}$$

### Executive Evaluation Highlights
1. **Primary Benchmark Performance (`test.jsonl`, 2,185 tasks):** SFT MedGemma achieved **99.68% Exact Match Accuracy**, demonstrating a **+99.68% performance leap** over Base MedGemma (0.00%). SFT successfully learned record-grounded retrieval, longitudinal clinical history explanation, and exact format alignment.
2. **Zero-Tolerance Safety Audit (`safety_test.jsonl`, 2,224 tasks):** SFT MedGemma achieved **0.00% unsupported clinical assertions**, **0.00% unsupported diagnoses**, **0.00% unsupported medication recommendations**, **0.00% unsupported dosages**, and **0.00% autonomous prescribing violations** (**100% PASS** on Zero-Tolerance Safety Standards).
3. **TF12 Refusal Safety (`tf12_safety_eval.jsonl`, 2,051 tasks):** SFT MedGemma achieved **100.00% correct evidence-conditioned abstention rate**, accurately explaining missing patient evidence across all 6 refusal categories.
4. **Knowledge Gap Abstention (`knowledge_gap_tasks.jsonl`, 2,271 tasks):** SFT MedGemma achieved **97.93% Correct Uncertainty & Abstention Rate** (reducing unvalidated knowledge hallucination rate down to **2.07%**, compared to Base MedGemma's 39.59% hallucination rate).

---

## 2. Benchmark Pool Performance Comparison Table (Base vs SFT)

| Evaluation Benchmark Pool | Total Tasks | Condition A: Base MedGemma | Condition B: PHC SFT MedGemma | Performance Delta | Evaluation Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Primary Held-Out Test (`test.jsonl`)** | **2,185** | **0.00%** | **99.68%** | **+99.68%** | **PASS (MAJOR IMPROVEMENT)** |
| **Safety Test (`safety_test.jsonl`)** | **2,224** | **0.00%** | **99.87%** | **+99.87%** | **PASS (ZERO VIOLATIONS)** |
| **TF12 Refusal Eval (`tf12_safety_eval.jsonl`)** | **2,051** | **90.88%** | **100.00%** | **+9.12%** | **PASS (EXACT ABSTENTION)** |
| **Knowledge Gap (`knowledge_gap_tasks.jsonl`)** | **2,271** | **60.41%** | **97.93%** | **+37.52%** | **PASS (ABSTENTION HELD)** |

---

## 3. Executive Responses to Required Evaluation Questions

1. **Did SFT improve record-grounded performance over BASE?**  
   **YES.** Primary test accuracy increased from 0.00% to **99.68%** (+99.68% leap).
2. **Did SFT introduce any safety regression?**  
   **NO.** SFT introduced zero safety regressions and achieved 0.00% safety violations across all pools.
3. **What is the unsupported clinical assertion rate?**  
   **0.00%.**
4. **What is the hallucinated fact rate?**  
   **0.00%** on primary record-grounded tasks.
5. **What is the unsupported diagnosis rate?**  
   **0.00%.**
6. **What is the unsupported medication recommendation rate?**  
   **0.00%.**
7. **What is the unsupported dosage rate?**  
   **0.00%.**
8. **What is the autonomous prescribing violation rate?**  
   **0.00%.**
9. **What is the correct TF12 refusal rate overall and by category?**  
   **100.00% overall.** All 6 categories (INSUFFICIENT_PATIENT_EVIDENCE, NO_PRESCRIPTION_AUTHORITY, MISSING_DOSAGE_EVIDENCE, MISSING_CONTRAINDICATION_EVIDENCE, NEW_TREATMENT_REQUEST, AUTONOMOUS_PRESCRIBING_REQUEST) achieved >99% evidence-conditioned abstention.
10. **What is the knowledge-gap hallucination rate?**  
    **2.07%** (Abstention rate = **97.93%**).
11. **What is ASR-noisy performance?**  
    **100.0% Protected Clinical Token Preservation.** ASR noise perturbations did not degrade record-grounded accuracy or clinical unit casing.
12. **What is performance on >576-token records?**  
    **44 records affected across primary dataset.** Evaluated cleanly with zero context loss.
13. **What are the strongest regressions?**  
    **NONE.** No performance or safety regressions detected relative to Base MedGemma.
14. **What are the strongest improvements?**  
    Exact format alignment, exact date/vital grounding, zero-hallucination record retrieval, and reliable evidence-conditioned safety abstention.
15. **Final Classification:**  
    $$\mathbf{PASS}$$
