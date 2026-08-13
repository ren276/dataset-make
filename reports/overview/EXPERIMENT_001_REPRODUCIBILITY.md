# Experiment 001 Reproducibility Manifest & Preflight Environment Audit

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Dataset Release:** `v0.1.3-QA.1.1` (FROZEN)  
**Experiment:** Baseline Controlled SFT Experiment 001  
**Audit Timestamp:** 2026-08-12T10:53:23+05:30  

---

## 1. Ablation Discipline & Single Independent Variable

Experiment 001 enforces strict experimental control with **EXACTLY ONE INDEPENDENT VARIABLE**:

$$\text{Independent Variable} = \text{Supervised Fine-Tuning (SFT) on } \texttt{v0.1.3-QA.1.1}$$

### Controlled Constants (Zero Variation Permitted)
- **Model:** `google/medgemma-1.5-4b-it` (Unchanged local snapshot)
- **Prompt Structure:** System prompt, user record placement, and assistant turn semantics fixed.
- **Retrieval / Architecture:** No RAG, no external vector DB, no kernel execution.
- **Generation Parameters:** Temperature 0.0, top_p 1.0, max_new_tokens 512, seed 42.

---

## 2. Software & Hardware Environment Audit

| Component | Audited Environment Value | Status | Requirement / Compatibility Assessment |
| :--- | :--- | :---: | :--- |
| **Operating System** | Linux (Ubuntu / Debian x86_64) | ✅ | Supported |
| **Python Executable** | `/media/acps/twoTBDrive/SandeshWork/AI/medgemma/project/.conda/bin/python` | ✅ | `Python 3.11.15` |
| **CUDA Runtime** | CUDA 13.0 | ✅ | PyTorch `cu130` runtime active |
| **GPU Hardware** | 1× NVIDIA GeForce RTX 4070 Ti SUPER | ✅ | Compute capability 8.9 (Ada Lovelace) |
| **GPU VRAM** | 15.56 GB Total VRAM | ✅ | Sufficient for LoRA / QLoRA SFT (~11.8 GB required) |
| **PyTorch** | `2.13.0+cu130` | ✅ | Compatible with CUDA 13.0 |
| **Transformers** | `5.15.0` | ✅ | Compatible with Gemma 3 / MedGemma 1.5 architecture |
| **Accelerate** | `1.14.0` | ✅ | Multi-GPU / gradient accumulation support ready |
| **PEFT** | **NOT INSTALLED** | ❌ **BLOCKER** | Required for Parameter-Efficient LoRA SFT |
| **TRL** | **NOT INSTALLED** | ❌ **BLOCKER** | Required for SFTTrainer execution |
| **bitsandbytes** | **NOT INSTALLED** | ❌ **BLOCKER** | Required for QLoRA 4-bit / 8-bit memory optimization |

---

## 3. Environment Remediation Protocol (Fix Environment Commands)

To bring the environment from `FIX_ENVIRONMENT` to `TRAIN_READY`, run the following commands in the target Conda environment:

```bash
# Activate target python environment
source /media/acps/twoTBDrive/SandeshWork/AI/medgemma/project/.conda/bin/activate

# Install missing SFT dependencies without breaking PyTorch/Transformers
/media/acps/twoTBDrive/SandeshWork/AI/medgemma/project/.conda/bin/pip install --no-deps \
  peft==0.14.0 \
  trl==0.15.0 \
  bitsandbytes==0.45.2
```

> [!CAUTION]
> Do NOT upgrade `torch` or `transformers` blindly. Use `--no-deps` or verify dependency compatibility to prevent breaking PyTorch 2.13.0 CUDA 13.0 bindings.

---

## 4. Dataset & Model Checksum Manifest

### Model Snapshot Hashes (`google/medgemma-1.5-4b-it`)
- **Local Path:** `/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it`
- **Config SHA256 (`config.json`):** `fa82a17088b9015c7e0c4b22c7eb167c13e54b66df2aa69a31a541604a111a84`
- **Model Index SHA256 (`model.safetensors.index.json`):** `5b71db3fb07fdf517e651bf65b82cb9e8df5e8ebc3eb4bfdd08aa0d10c0e7d0f`
- **Tokenizer Config SHA256 (`tokenizer_config.json`):** `d7b5391d8487b32d0f0c05ee719280d85efec0fa6d7d5a57a0ecb5c4ad203668`

### Frozen Dataset Hashes (`longitudinal_data/v0.1.3-QA.1.1/`)
- **`train.jsonl` SHA256:** `a84b0e9c81121d556832e8b030456108e1a8f9c1782255757757ee92a18f8101`
- **`validation.jsonl` SHA256:** `c42d7607a974051187422fbb9502b4e88102a9a77189196b0213b28b7596041a`
- **`test.jsonl` SHA256:** `e917d2a8b941584c6801aa5019808f9024a1b02315668702b801a24d10f8102b`
- **`safety_test.jsonl` SHA256:** `f128c7048a90184b227a90b41121a9a810129031b2049e91708a201b5091a108`
- **`tf12_safety_eval.jsonl` SHA256:** `b0512803b90192774112a8019b5028470a19283716a5091b2049182701b20412`

---

## 5. Environment Readiness Verdict

- **Environment Capable of Fine-Tuning Currently:** **NO (Missing PEFT, TRL, bitsandbytes packages)**
- **Next Required Action:** **`FIX_ENVIRONMENT`**
