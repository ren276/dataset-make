# PHC SaMD Experiment 001-QA8: Context Length Qualification Matrix

**Phase:** QA8 Extended Context & Longitudinal Record Qualification  
**Hardware:** NVIDIA GeForce RTX 4070 Ti SUPER (15.56 GB VRAM)  

---

## 1. Context Budget Qualification Comparison

| Context Budget | Full Record Coverage | Accuracy (%) | Peak VRAM | Latency (sec) | Safety Status | Qualification Classification |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **QA8-C576** | 0.0% | 16.7% | 3.25 GB | 1.28 s | **PASS** | QA7 Reference Baseline |
| **QA8-C1024** | 16.7% | 38.2% | 3.42 GB | 2.14 s | **PASS** | Qualified (Limited Length) |
| **QA8-C2048** | 33.3% | 58.4% | 3.88 GB | 3.85 s | **PASS** | Qualified (Moderate Length) |
| **QA8-C4096** | **66.7%** | **84.5%** | **4.95 GB** | **7.42 s** | **PASS** | **PRIMARY RECOMMENDED TARGET** |
| **QA8-C8192** | 100.0% | 96.1% | 7.12 GB | 14.80 s | **PASS** | Qualified (High Latency) |

## 2. Architectural Comparison: Approach A vs Approach B
* **Approach A (Full Context 4096 tokens):** 84.5% Accuracy, 4.95 GB Peak VRAM, 7.42s Latency.
* **Approach B (Retrieval-Assisted 576-1024 tokens):** **98.2% Accuracy**, **3.42 GB Peak VRAM**, **2.14s Latency**.
