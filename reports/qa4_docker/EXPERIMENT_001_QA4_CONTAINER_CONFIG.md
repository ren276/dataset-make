# PHC SaMD Experiment 001-QA4: Container Configuration Specification

**Phase:** Phase 1 Container Design & Specification  

---

## 1. Container Architecture & Mount Strategy
* **Base Image:** `nvidia/cuda:12.0.0-base-ubuntu22.04`
* **Python Runtime:** `Python 3.11.15`
* **CUDA Driver Compatibility:** NVIDIA Driver `580.126.09` / CUDA `13.0`
* **GPU Acceleration:** NVIDIA Container Toolkit (`--gpus all`)
* **Volume Mounts (ReadOnly):**
  * `/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it` -> `/models/medgemma-1.5-4b-it:ro`
  * `/media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/final_adapter` -> `/models/final_adapter:ro`

## 2. Docker Run Command Specification
```bash
docker run -d \
  --gpus all \
  --name phc_samd_qa4_inference \
  -p 8000:8000 \
  -v /media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it:/models/medgemma-1.5-4b-it:ro \
  -v /media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/final_adapter:/models/final_adapter:ro \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  phc_samd_qa4:latest
```
