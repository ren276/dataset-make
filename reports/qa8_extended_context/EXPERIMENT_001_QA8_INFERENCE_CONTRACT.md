# PHC SaMD Experiment 001-QA8: Extended Context Inference Contract

**Phase:** QA8 Inference Contract Specification  

---

## 1. Locked Generation Parameters
* **`do_sample`:** `false` (Greedy Decoding)
* **`temperature`:** `0.0`
* **`max_new_tokens`:** `256`
* **`max_input_length`:** `4096` tokens (Primary Target) / `8192` tokens (Extended Max)
* **Template Rendering:** Native MedGemma Chat Template (`tokenizer.apply_chat_template`)
