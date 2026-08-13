# PHC SaMD Experiment 001-QA3: Exact Inference Contract Specification

**Phase:** Phase 2 Exact Inference Contract  

---

## 1. Deterministic Inference Parameters
* **`do_sample`:** `false` (Deterministic greedy decoding)
* **`temperature`:** `0.0`
* **`max_new_tokens`:** `256`
* **`max_input_length`:** `576` tokens (Enforced max length from Experiment 001-QA2)
* **`PYTORCH_CUDA_ALLOC_CONF`:** `expandable_segments:True`

## 2. Chat Template & Formatting Integrity
* **Chat Template:** Native MedGemma chat template applied via `tokenizer.apply_chat_template()`
* **System Prompt:** Preserved exact project system prompt without alteration.
* **Role Mapping:** System (`<start_of_turn>system...`), User (`<start_of_turn>user...`), Model (`<start_of_turn>model...`).
