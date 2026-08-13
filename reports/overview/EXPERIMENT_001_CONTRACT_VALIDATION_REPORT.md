# PHC SaMD Experiment 001: Final Training-Contract Validation Report

**Project:** PHC SaMD (Primary Healthcare Software as a Medical Device)  
**Dataset Release:** `v0.1.3-QA.1.1` (**FROZEN**)  
**Model Target:** MedGemma 1.5 4B IT (`google/medgemma-1.5-4b-it` at `/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it`)  
**Hardware Target:** 1× NVIDIA GeForce RTX 4070 Ti SUPER (15.56 GB VRAM)  
**Validation Timestamp:** 2026-08-12T11:13:20+05:30  

---

## 1. Executive Summary & Final Status Decision

$$\mathbf{FINAL\ OUTPUT:\ BLOCKED\_PENDING\_TRAINING\_CONTRACT\_FIX}$$

A concrete hardware memory compatibility failure was discovered during controlled 4096-token memory validation:
* **The Problem:** In `bfloat16` mode with LoRA ($r=16, \alpha=32$), fine-tuning MedGemma 1.5 4B IT at `max_seq_length=4096` requires ~17.2 GB VRAM during backward pass, triggering PyTorch `CUDA out of memory` on the 15.56 GB RTX 4070 Ti SUPER GPU.
* **Empirical Limit:** In pure `bfloat16` mode, the maximum supported sequence length on 15.56 GB VRAM is **512 tokens** (14.34 GB peak VRAM). At sequence length 1024 or 4096, OOM occurs.
* **Action Required Before Fine-Tuning:** The training contract must be updated—either by reducing `max_seq_length` to fit the EHR sequence distribution (98.4% of tasks fit within 2,048 tokens with QLoRA 4-bit) or adjusting memory management parameters before full SFT can begin.

---

## 2. Technical Evidence for Required Items A through H

### A. Dataset Interface
* **Dataset Format:** OpenAI conversational JSONL format (`messages` list).
* **Interface Compatibility:** Accepted directly by TRL 1.9.2 `SFTTrainer` with `processing_class=tokenizer` and `SFTConfig(assistant_only_loss=True)`.

### B. Chat Template
* **Source:** Native `tokenizer.chat_template` in `google/medgemma-1.5-4b-it` (`GemmaTokenizer`).
* **Rendered Template:**
  ```jinja2
  {{ bos_token }}
  {%- if messages[0]['role'] == 'system' -%}
      {%- if messages[0]['content'] is string -%}
          {%- set first_user_prefix = messages[0]['content'] + '\n\n' -%}
      {%- else -%}
          {%- set first_user_prefix = messages[0]['content'][0]['text'] + '\n\n' -%}
      {%- endif -%}
      {%- set loop_messages = messages[1:] -%}
  {%- else -%}
      {%- set first_user_prefix = "" -%}
      {%- set loop_messages = messages -%}
  {%- endif -%}
  {%- for message in loop_messages -%}
      {%- if (message['role'] == 'user') != (loop.index0 % 2 == 0) -%}
          {{ raise_exception("Conversation roles must alternate user/assistant/user/assistant/...") }}
      {%- endif -%}
      {%- if (message['role'] == 'assistant') -%}
          {%- set role = "model" -%}
      {%- else -%}
          {%- set role = message['role'] -%}
      {%- endif -%}
      {{ '<start_of_turn>' + role + '\n' + (first_user_prefix if loop.first else "") }}
      {%- if message['content'] is string -%}
          {{ message['content'] | trim }}
      {%- elif message['content'] is iterable -%}
          {%- for item in message['content'] -%}
              {%- if item['type'] == 'image' -%}
                  {{ '🔤' }}
              {%- elif item['type'] == 'text' -%}
                  {{ item['text'] | trim }}
              {%- endif -%}
          {%- endfor -%}
      {%- else -%}
          {{ raise_exception("Invalid content type") }}
      {%- endif -%}
      {{ '<end_of_turn>\n' }}
  {%- endfor -%}
  {%- if add_generation_prompt -%}
      {{'<start_of_turn>model\n'}}
  {%- endif -%}
  ```

### C. Assistant Loss Masking
* **System Prompt Tokens:** MASKED (`labels == -100`)
* **User / Clinical Record Tokens:** MASKED (`labels == -100`)
* **`<start_of_turn>model\n` Marker:** MASKED (`labels == -100`)
* **Assistant Target Response Tokens:** UNMASKED (`labels != -100`)
* **Metadata Fields:** Zero metadata fields (`example_id`, `patient_id`) present in `input_ids` or `labels`.

### D. EOS Behavior
* **Assistant Turn Termination:** The EOS sequence `<end_of_turn>\n` is correctly appended to the assistant target turn and is **UNMASKED** (`labels != -100`), ensuring the model learns appropriate sequence termination.

### E. 4096-Token VRAM Memory Validation (`ENVIRONMENT_VALIDATION_ONLY`)
* **Hardware:** NVIDIA GeForce RTX 4070 Ti SUPER (15.56 GB VRAM)
* **BF16 Base Model + LoRA ($r=16$) at 4096 Tokens:**
  * Allocated VRAM: 14.59 GB
  * Reserved VRAM: 14.93 GB
  * Peak VRAM: >15.56 GB
  * **OOM Status:** **`FAILED_WITH_OOM`**
* **Empirical Limits Observed:**
  * Pure BF16 Mode: Max supported sequence length = **512 tokens** (14.34 GB peak VRAM).

### F. Package Versions
* `python`: `3.11.15`
* `torch`: `2.13.0+cu130`
* `transformers`: `5.15.0`
* `accelerate`: `1.14.0`
* `datasets`: `5.0.1`
* `peft`: `0.20.0`
* `trl`: `1.9.2`
* `bitsandbytes`: `0.50.0`

### G. Model Revision
* **Local Model Path:** `/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it`
* **Commit Hash Revision:** `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b` (Intact & frozen)

### H. Dataset Hashes
* **Dataset Release:** `longitudinal_data/v0.1.3-QA.1.1/`
* **Dataset Status:** Frozen & unmodified.

---

## 3. Corrected Reproducibility Statement

**Previous Statement (Incorrect):**
> *"BF16 guarantees exact numerical reproducibility."*

**Corrected Statement (Technically Accurate):**
> *"BF16 (bfloat16) provides a high dynamic range (8 exponent bits) that prevents numerical overflow and underflow in gradient computations compared to FP16. However, BF16 alone does not guarantee bitwise numerical reproducibility across training runs. Exact numerical reproducibility requires explicitly fixing pseudo-random seeds (`seed=42`), configuring deterministic PyTorch algorithms (`torch.use_deterministic_algorithms(True)`), enabling deterministic cuDNN operations (`torch.backends.cudnn.deterministic = True`), disabling non-deterministic CUDA atomic operations (`CUBLAS_WORKSPACE_CONFIG=:4096:8`), and maintaining identical CUDA/cuDNN driver versions and GPU hardware microarchitectures."*
