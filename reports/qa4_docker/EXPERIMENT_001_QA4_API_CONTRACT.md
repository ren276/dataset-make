# PHC SaMD Experiment 001-QA4: API Contract

**Phase:** Phase 5 API Layer Specification  

---

## Endpoint Definition
* **URL:** `POST /v1/record-grounded-inference`
* **Headers:** `Content-Type: application/json`

### Request Body Schema
```json
{
  "clinical_context": "Patient Record Text...",
  "instruction": "Question about patient record..."
}
```

### Response Body Schema
```json
{
  "example_id": "QA4_INF_001",
  "prediction": "The patient's diagnosis of Gingivitis (disorder) was recorded on 2024-05-18.",
  "latency_sec": 0.852,
  "status": "SUCCESS"
}
```
