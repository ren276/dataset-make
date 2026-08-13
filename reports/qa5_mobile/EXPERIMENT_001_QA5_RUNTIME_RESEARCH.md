# PHC SaMD Experiment 001-QA5: Android Runtime Feasibility Research Report

**Audit Timestamp:** 2026-08-12T23:41:00+05:30  
**Phase:** Phase 0 Research Current & Supported Android Runtimes  

---

## 1. Executive Summary & Runtime Decision Matrix

| Evaluation Criterion | Google LiteRT / MediaPipe GenAI | llama.cpp / GGUF ARM64 Runtime | Technical Assessment |
| :--- | :--- | :--- | :--- |
| **Gemma / MedGemma Architecture Support** | Supported via PyTorch exporter | Native Gemma architecture support ( / ) | Both support Gemma vision/language layers |
| **LoRA Fine-Tuned Weights Support** | Requires pre-merged PyTorch model | Requires merged HF model -> GGUF | Both require derived merged bfloat16 model |
| **Quantization Methods** | int8 / int4 symmetric weight quantization | Q4_K_M, Q5_K_M, Q8_0 K-quants | GGUF offers finer memory/quality tradeoffs |
| **Android Hardware Acceleration** | OpenCL, Vulkan, NPU Delegate | Vulkan GPU + CPU ARM NEON SIMD | LiteRT leads NPU; llama.cpp leads CPU fallback |
| **Tokenizer & Template Integrity** |  sentencepiece SPM | Native Jinja template embedded in GGUF | Both preserve exact MedGemma chat template |
