# PHC SaMD Experiment 001-QA3: Runtime Characterization Report

**Phase:** Phase 4 Runtime Characterization  
**Hardware:** NVIDIA GeForce RTX 4070 Ti SUPER (15.56 GB VRAM)  

---

## 1. Input Length Percentile Benchmarks

| Percentile | Input Tokens | Generated Tokens | Avg Latency (sec) | Throughput (tok/sec) | Peak Allocated VRAM | CPU RAM |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **P50** | 119 | 27.0 | 1.271 s | 21.2 tok/s | 3.21 GB | 1.83 GB |
| **P90** | 251 | 157.0 | 7.396 s | 21.2 tok/s | 3.24 GB | 1.83 GB |
| **P95** | 279 | 185.0 | 8.639 s | 21.4 tok/s | 3.24 GB | 1.83 GB |
| **P99** | 309 | 218.0 | 10.230 s | 21.3 tok/s | 3.25 GB | 1.83 GB |
| **Longest_714** | 398 | 256.0 | 11.976 s | 21.4 tok/s | 3.26 GB | 1.83 GB |
| **Boundary_576** | 294 | 200.0 | 9.512 s | 21.0 tok/s | 3.24 GB | 1.83 GB |
