# PHC SaMD Experiment 001-QA7: Dockerized MedGemma Research Service Plan

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Title:** Dockerized MedGemma Inference Service + Local Chat Interface  
**Scope:** Controlled Research Inference Interface (**Localhost Only**)  

---

## 1. Architectural Topology
```
Browser UI (Localhost:8000)
    │
    ▼
FastAPI REST Service (Uvicorn / Python 3.11)
    │
    ▼
HuggingFace Transformers + PEFT LoRA (4-bit NF4)
    │
    ▼
MedGemma 1.5 4B IT + Frozen PHC LoRA Adapter
    │
    ▼
NVIDIA RTX 4070 Ti SUPER GPU (15.56 GB VRAM)
```

## 2. Intended Research Scope & Strict Safety Boundaries
* **Intended Capability:** Historical record retrieval, observation explanation, encounter summarization, and safe record-grounded abstention.
* **Prohibited Capabilities:** Diagnostic engine, treatment recommender, medication selection, dosage determination, prescribing action.
