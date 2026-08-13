# PHC SaMD Experiment 001-QA2: Reproducibility Specification

**Experiment Identifier:** `EXPERIMENT_001_QA2`  
**Dataset Release:** `v0.1.3-QA.1.1` (**FROZEN**)  
**Model Path:** `/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it`  
**Model Commit Revision:** `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b`  

---

## 1. Single Independent Variable Discipline

Experiment 001-QA2 isolates exactly one independent variable: **Record-Grounded SFT on frozen release `v0.1.3-QA.1.1` using QLoRA 4-bit NF4 at `max_length=512`**.

All auxiliary variables remain strictly controlled:
* **Model:** MedGemma 1.5 4B IT (Unchanged)
* **Prompt Format:** MedGemma 1.5 4B IT Native Jinja2 Template (Unchanged)
* **Retrieval / RAG:** Disabled
* **NLEM Retrieval:** Disabled
* **Clinical Kernel:** Disabled
* **Teacher LLM:** Disabled

---

## 2. Technical Reproducibility Protocol

To ensure exact numerical reproducibility across training runs:
1. Fix pseudo-random seed: `seed=42`.
2. Configure PyTorch deterministic algorithms: `torch.use_deterministic_algorithms(True)`.
3. Enable cuDNN deterministic backend: `torch.backends.cudnn.deterministic = True`.
4. Configure CUDA atomic operations environment variable: `export CUBLAS_WORKSPACE_CONFIG=:4096:8`.

---

## 3. Dataset SHA256 Manifest

| Dataset File Path | Record Count | File Size (Bytes) | SHA256 Checksum |
| :--- | :---: | :---: | :--- |
| `longitudinal_data/v0.1.3-QA.1.1/train.jsonl` | 1,915 | 2,571,477 | `0574489d5023db3c6ae574e791a5a09fe5d6ac9cce03d6292ff78eeb9198a0f6` |
| `longitudinal_data/v0.1.3-QA.1.1/validation.jsonl` | 328 | 440,892 | `026dda2a5109460a050956dec7f647f7a04b788b6cf6b9907c5bbce0a208cbc1` |
| `longitudinal_data/v0.1.3-QA.1.1/test.jsonl` | 289 | 387,417 | `38d6bf89f320e06c42d94d7ff11c0caf040af2b9fb68035d87bf5d2649c7a83a` |
| `longitudinal_data/v0.1.3-QA.1.1/safety_test.jsonl` | 19,683 | 26,401,580 | `871fd40c6dec7dce2db437b3a097fdd6cbe781da545047c3681d51758ff065f0` |
| `longitudinal_data/v0.1.3-QA.1.1/tf12_safety_eval.jsonl` | 2,222 | 2,980,510 | `00a559cd5fea12139f311ac6100cd2737ac4dddbe2ee1abd7163443e386a51b6` |
| `longitudinal_data/v0.1.3-QA.1.1/knowledge_gap/knowledge_gap_tasks.jsonl` | 2,469 | 3,313,143 | `e27f7a969c45f3d267cdb29a334b3843da0620930ba604571d0645e6e46beaba` |
