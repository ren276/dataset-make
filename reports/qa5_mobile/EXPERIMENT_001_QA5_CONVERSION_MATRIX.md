# PHC SaMD Experiment 001-QA5: Model Conversion & Quantization Matrix

**Phase:** Phase 1 Conversion Feasibility & Derivation Strategy  

---

## 1. Derived Merged Model Provenance
* **Source Base Model:**  (Revision: )
* **Source LoRA Adapter:**  (**UNTOUCHED & FROZEN**)
* **Derived Merged Artifact Path:** 
* **Derived Model Size:** 8.04 GB

## 2. Quantization Format & Runtime Compatibility Matrix

| Candidate Format | Target Runtime | Model File Size | Estimated RAM | Context Window | Mobile Viability |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **bfloat16 Merged** | Host / High-end Edge | 8.6 GB | ~10 GB | 576 tokens | High-end Edge / Desktop |
| **GGUF Q4_K_M** | llama.cpp ARM64 Android | 2.6 GB | ~3.4 GB | 576 tokens | **RECOMMENDED (HIGH COMPATIBILITY)** |
| **GGUF Q5_K_M** | llama.cpp ARM64 Android | 3.1 GB | ~4.0 GB | 576 tokens | High-end Android Devices |
| **LiteRT int4** | Google AI Edge / MediaPipe | 2.4 GB | ~3.2 GB | 576 tokens | **RECOMMENDED (GOOGLE NPU ACCELERATED)** |
