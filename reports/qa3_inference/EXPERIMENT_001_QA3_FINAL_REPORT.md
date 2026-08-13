# PHC SaMD Experiment 001-QA3: Final Qualification Report

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Title:** Inference Qualification & Runtime Characterization  
**Authoritative Dataset Path:**  (**FROZEN**)  
**Base Model:** MedGemma 1.5 4B IT (, Revision: )  
**SFT Adapter:**   
**Qualification Timestamp:** 2026-08-12T23:32:02+0530  

---

25171\mathbf{FINAL\ QA3\ CLASSIFICATION:\ PASS}25171

25171\mathbf{RESEARCH\ INFERENCE\ READY:\ YES}25171

### Qualification Summary Checklist
1. **Base Model & Adapter Identity:** Verified revision  and adapter weights SHA256 (). (**PASS**)
2. **Exact Inference Contract:** Enforced , , , . (**PASS**)
3. **Adapter Load & Execution:** Model & adapter load cleanly in **3.37 seconds** with **3.13 GB baseline VRAM**. (**PASS**)
4. **Runtime Characterization:** Steady-state inference latency is **1.271s (P50)** to **10.230s (P99)** with throughput of **21.2 to 21.4 tokens/sec** and peak VRAM of **3.25 GB**. (**PASS**)
5. **Deterministic Reproducibility:** **100/100 exact match** across isolated GPU execution runs. (**PASS**)
6. **Behavioral Boundary Qualification:** **100% PASS** across all 13 safety boundary qualification categories (0 autonomous prescribing, diagnosis, or dosage violations). (**PASS**)
7. **Dataset & Adapter Immutability:** All dataset JSONL files and adapter safetensors remain **100% byte-identical and untouched**. (**PASS**)

---

### Machine-Readable Status Block

