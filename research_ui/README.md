# PHC SaMD MedGemma Research Interface (research_ui)

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Component:** Standalone Browser Research Interface  
**API Endpoint:** `POST /v1/chat` (`http://localhost:8000`)  

---

## 1. Architecture Overview
This directory contains the decoupled, standalone web frontend for interacting with the qualified MedGemma 1.5 4B IT + frozen PHC LoRA inference service.

```
research_ui/
├── index.html        # Clean HTML5 structure & warning banner
├── css/
│   └── style.css     # Slate/dark modern UI styling
├── js/
│   └── app.js        # Configurable API client & chat session state
└── README.md         # Documentation
```

## 2. Intended Scope & Disclaimers
* **RESEARCH USE ONLY:** This interface is explicitly designed for research qualification and record-grounded SLM evaluation.
* **NOT FOR CLINICAL USE:** This interface is NOT a diagnostic engine, treatment recommender, dosage engine, or prescribing system.
* **DECOUPLED DESIGN:** Contains 0 model weights, 0 inference logic, and 0 clinical decision paths. All generation is executed over the qualified FastAPI service.
