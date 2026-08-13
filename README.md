# PHC SaMD (Primary Healthcare Software as a Medical Device) — Research Experiment Suite

**Project:** Record-Grounded Small Language Model (SLM) Research Qualification  
**Base Model:** MedGemma 1.5 4B IT (`google/medgemma-1.5-4b-it`, Revision: `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b`)  
**Fine-Tuned Adapter:** PHC SaMD Experiment 001-QA2 LoRA Adapter ([experiment_001_qa2_output/final_adapter](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/final_adapter))  
**Authoritative Dataset Path:** [longitudinal_data/authoritative/v0.1.3-QA.1.1/](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/longitudinal_data/authoritative/v0.1.3-QA.1.1/) (**FROZEN**)  

---

## 📁 Repository Structure & Directory Organization

```
dataset-make/
├── longitudinal_data/              # Authoritative frozen release dataset (v0.1.3-QA.1.1)
├── experiment_001_qa2_output/      # Fine-tuned PHC LoRA adapter weights (final_adapter)
├── research_ui/                    # QA7 Decoupled Browser Research Interface (576-token budget)
├── research_ui_qa8/                # QA8 Decoupled Browser Research Interface (4096-token budget)
│
├── app_server.py                   # QA7 Local Research Service Server (576-token limit)
├── app_server_qa8.py               # QA8 Local Research Service Server (4096-token limit)
│
├── scripts/                        # Python Qualification Pipeline & Execution Scripts
│   ├── run_experiment_001_qa2_sft.py # QA2 3-Epoch SFT Training Pipeline
│   ├── run_post_sft_evaluation.py    # QA2 Post-SFT Benchmark Evaluation
│   ├── run_qa3_phases0_3.py          # QA3 Inference Qualification (Phases 0 - 3)
│   ├── run_qa3_phases4_10.py         # QA3 Inference Qualification (Phases 4 - 10)
│   ├── run_qa4_pipeline.py           # QA4 Containerized GPU Qualification Pipeline
│   ├── run_qa5_phases2_13.py         # QA5 Mobile Feasibility Pipeline
│   ├── run_qa7_pipeline.py           # QA7 Research Service & Local Chat UI Pipeline
│   ├── run_qa8_benchmarks.py         # QA8 Extended Context Qualification Pipeline
│   ├── generate_qa8_corpus.py        # QA8 Longitudinal Evaluation Corpus Generator
│   └── validate_ui_separation.py     # QA7 UI Separation Validation Script
│
└── reports/                        # Structured Experiment Reports & Artifacts
    ├── overview/                   # Overall Plans, Safety Evaluations & Hash Manifests
    ├── qa2_sft/                    # QA2 SFT Training & Evaluation Reports
    ├── qa3_inference/              # QA3 Native GPU Inference Qualification Reports
    ├── qa4_docker/                 # QA4 Containerized GPU Qualification Reports
    ├── qa5_mobile/                 # QA5 Mobile Feasibility Qualification Reports
    ├── qa7_service_ui/             # QA7 Research Service & UI Separation Audit Reports
    └── qa8_extended_context/       # QA8 Extended Context Qualification Reports
```

---

## 🎯 Qualification Lifecycle Summary

| Experiment Milestone | Primary Objective | Output Classification | Primary Artifacts |
| :--- | :--- | :--- | :--- |
| **Experiment 001-QA2** | 3-Epoch Supervised Fine-Tuning & Evaluation | `VALIDATED_PASS` | [reports/qa2_sft/EXPERIMENT_001_QA2_EVALUATION_REPORT.md](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/reports/qa2_sft/EXPERIMENT_001_QA2_EVALUATION_REPORT.md) |
| **Experiment 001-QA3** | Native GPU Inference Qualification | `QA3_STATUS: PASS` | [reports/qa3_inference/EXPERIMENT_001_QA3_FINAL_REPORT.md](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/reports/qa3_inference/EXPERIMENT_001_QA3_FINAL_REPORT.md) |
| **Experiment 001-QA4** | Containerized GPU Inference Qualification | `QA4_STATUS: PASS` | [reports/qa4_docker/EXPERIMENT_001_QA4_FINAL_REPORT.md](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/reports/qa4_docker/EXPERIMENT_001_QA4_FINAL_REPORT.md) |
| **Experiment 001-QA5** | Mobile Inference Feasibility & Conversion | `MOBILE_FEASIBLE_WITH_LIMITATIONS` | [reports/qa5_mobile/EXPERIMENT_001_QA5_FINAL_REPORT.md](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/reports/qa5_mobile/EXPERIMENT_001_QA5_FINAL_REPORT.md) |
| **Experiment 001-QA7** | Dockerized GPU Service + Decoupled UI | `DOCKER_RESEARCH_INFERENCE_QUALIFIED` | [reports/qa7_service_ui/EXPERIMENT_001_QA7_FINAL_REPORT.md](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/reports/qa7_service_ui/EXPERIMENT_001_QA7_FINAL_REPORT.md) |
| **Experiment 001-QA8** | Extended Context (4096 Tokens) Qualification | `QA8-4096-QUALIFIED-WITH-RETRIEVAL` | [reports/qa8_extended_context/EXPERIMENT_001_QA8_FINAL_REPORT.md](file:///media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/reports/qa8_extended_context/EXPERIMENT_001_QA8_FINAL_REPORT.md) |

---

## 🚀 Running the Local Research Service & Scripts

### Run Research Services
```bash
# QA7 Service (576-token limit)
python -m uvicorn app_server:app --host 127.0.0.1 --port 8000

# QA8 Service (4096-token extended context)
python -m uvicorn app_server_qa8:app --host 127.0.0.1 --port 8000
```

### Run Qualification Pipelines
```bash
python scripts/run_qa8_benchmarks.py
python scripts/validate_ui_separation.py
```
