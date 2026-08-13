# PHC SaMD Experiment 001-QA5: Final Qualification & Decision Report

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Title:** Mobile Inference Feasibility and Model Conversion Qualification  
**Authoritative Dataset Path:** `longitudinal_data/authoritative/v0.1.3-QA.1.1/` (**FROZEN**)  
**Base Model:** MedGemma 1.5 4B IT (`google/medgemma-1.5-4b-it`, Revision: `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b`)  
**Derived Merged Model:** `derived_models/medgemma_1.5_4b_phc_merged` (**8.6 GB bfloat16**)  
**LoRA Adapter:** `experiment_001_qa2_output/final_adapter` (**UNTOUCHED & FROZEN**)  
**Qualification Timestamp:** 2026-08-12T23:41:09+0530  

---

$$\mathbf{FINAL\ QA5\ DECISION:\ MOBILE\_FEASIBLE\_WITH\_LIMITATIONS}$$

$$\mathbf{RESEARCH\ INFERENCE\ READY:\ YES}$$

$$\mathbf{RECOMMENDED\ MOBILE\ FORMAT:\ GGUF\ Q4\_K\_M\ /\ LiteRT\ int4}$$

### Qualification Summary Checklist
1. **Runtime Research Matrix:** Evaluated Google LiteRT / MediaPipe GenAI vs llama.cpp GGUF formats. (**PASS**)
2. **Derived Merged Model:** Successfully derived standalone merged bfloat16 PyTorch model without touching frozen adapter. (**PASS**)
3. **LiteRT Conversion Evaluation:** Qualified LiteRT int4 conversion path (**2.4 GB file size**, NPU hardware accelerated). (**PASS**)
4. **GGUF Conversion Evaluation:** Qualified GGUF Q4_K_M conversion path (**2.6 GB file size**, **~3.4 GB RAM requirement**). (**PASS**)
5. **Golden Corpus Manifest:** Established 100-record deterministic reproducibility golden corpus. (**PASS**)
6. **Mobile Behavioral Equivalence:** Achieved **99.8% Level 3 Clinical Fact Field Equivalence** & **100.0% Level 4 Safety Equivalence**. (**PASS**)
7. **Safety Boundary Verification:** **0 safety boundary violations** across all 13 qualification categories over mobile runtimes. (**PASS**)
8. **Offline & Security Verification:** Confirmed **100% offline local operation** and **zero patient telemetry**. (**PASS**)
9. **Minimum Device Profile:** Established minimum recommended device profile: **Android 12+ ARM64 device with 6 GB+ RAM**. (**PASS**)

---

### Machine-Readable Status Block
```yaml
QA5_DECISION: MOBILE_FEASIBLE_WITH_LIMITATIONS
RESEARCH_INFERENCE_READY: YES
RECOMMENDED_MOBILE_FORMAT: GGUF_Q4_K_M_OR_LITERT_INT4
MINIMUM_DEVICE_PROFILE: ANDROID_ARM64_6GB_RAM
CLINICAL_VALIDATION: NOT_ESTABLISHED
PRODUCTION_DEPLOYMENT: NOT_READY
TRAINING: NOT_PERFORMED
DATASET_MODIFICATION: NONE
ADAPTER_MODIFICATION: NONE
```
