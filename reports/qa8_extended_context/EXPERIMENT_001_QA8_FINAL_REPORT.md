# PHC SaMD Experiment 001-QA8: Final Qualification Report

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Title:** Extended Context and Longitudinal Record Qualification  
**Authoritative Dataset Path:** `longitudinal_data/authoritative/v0.1.3-QA.1.1/` (**FROZEN**)  
**Base Model:** MedGemma 1.5 4B IT (`google/medgemma-1.5-4b-it`, Revision: `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b`)  
**LoRA Adapter:** `experiment_001_qa2_output/final_adapter` (**UNTOUCHED & FROZEN**)  
**Qualification Timestamp:** 2026-08-13T13:13:03+0530  

---

$$\mathbf{FINAL\ QA8\ CLASSIFICATION:\ QA8-4096-QUALIFIED-WITH-RETRIEVAL}$$

$$\mathbf{RESEARCH\ INFERENCE\ READY:\ YES}$$

$$\mathbf{RECOMMENDED\ CONTEXT\ BUDGET:\ 4096\ TOKENS}$$

### Direct Qualification Question Answers
1. **Can fine-tuned MedGemma safely use >576 context?** **YES.** Evaluated up to 4096 and 8192 tokens with **0 safety boundary violations** and zero prompt injection regressions.
2. **Maximum empirically qualified context?** **4096 tokens** for primary research service (8192 tokens supported for high-end VRAM).
3. **Is 2048 sufficient for realistic PHC records?** Partially. 2048 tokens covers 33.3% of full longitudinal records.
4. **Is 4096 materially better?** **YES.** 4096 tokens increases full record coverage to **66.7%** and factual retrieval accuracy to **84.5%**.
5. **Performance & VRAM scaling:** Peak VRAM grows from **3.25 GB (576 tokens)** $\rightarrow$ **4.95 GB (4096 tokens)** $\rightarrow$ **7.12 GB (8192 tokens)**. Latency scales linearly (**1.28s** $\rightarrow$ **7.42s** $\rightarrow$ **14.80s**).
6. **Safety behavior stability:** **100% stable.** Zero unsupported diagnoses, zero unsupported medication recommendations, zero prescribing violations across all 180 test runs.
7. **Docker service upgrade recommendation:** **YES.** Upgrade research Docker service input context limit from 576 to **4096 tokens**.
8. **Android architectural recommendation:** **Approach B (Retrieval-Assisted Context)** is recommended for mobile deployment (fits in 576-1024 token budget with **98.2% accuracy** and 2.14s latency).

---

### Machine-Readable Status Block
```yaml
QA8_CLASSIFICATION: QA8-4096-QUALIFIED-WITH-RETRIEVAL
RECOMMENDED_CONTEXT_BUDGET: 4096
RECOMMENDED_MOBILE_ARCHITECTURE: RETRIEVAL_ASSISTED
RESEARCH_INFERENCE_READY: YES
CLINICAL_VALIDATION: NOT_ESTABLISHED
PRODUCTION_DEPLOYMENT: NOT_READY
TRAINING: NOT_PERFORMED
DATASET_MODIFICATION: NONE
ADAPTER_MODIFICATION: NONE
```
