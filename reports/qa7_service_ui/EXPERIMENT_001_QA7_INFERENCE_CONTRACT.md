# PHC SaMD Experiment 001-QA7: Qualified Inference & API Contract

**Phase:** QA7 Qualified Inference Contract  

---

## 1. Generation Contract Parameters
* **`do_sample`:** `false` (Deterministic greedy decoding)
* **`temperature`:** `0.0`
* **`max_new_tokens`:** `256`
* **`max_input_length`:** `576` tokens (Strict Context Enforced)
* **Template Rendering:** Native MedGemma Chat Template (`tokenizer.apply_chat_template`)
