# PHC SaMD Experiment 001-QA3: Model & Adapter Identity Verification

**Phase:** Phase 1 Model + Adapter Identity Verification  

---

## 1. Base Model Identity
* **Model ID:** `google/medgemma-1.5-4b-it`
* **Local Path:** `/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it`
* **Revision:** `91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b` (**MATCHES EXACT REQUIREMENT**)

## 2. LoRA Adapter Architecture & Parameters
* **Adapter Path:** `/media/acps/twoTBDrive/SandeshWork/AI/syntheadataset/dataset-make/experiment_001_qa2_output/final_adapter`
* **LoRA Rank ($r$):** `16`
* **LoRA Alpha ($lpha$):** `32`
* **LoRA Dropout:** `0.05`
* **Target Modules:** `up_proj, down_proj, q_proj, v_proj, gate_proj, o_proj, k_proj`
* **Trainable Parameter Count:** `32,788,480`

## 3. Adapter File Checksums
* `tokenizer_config.json` (770 bytes): SHA256=`4a9056b0e6b60c047b811bf260d2f01a7e7b19790fdb1b071f7ab51064619f01`
* `training_args.bin` (5,265 bytes): SHA256=`044bfd57bdffe11d702bf38ee0c1b81cf869d3d17f528e98ffa7fa459c68f0cd`
* `adapter_config.json` (1,205 bytes): SHA256=`f46b9553b08aff22df46d767816ebaf06ec621835c89da921a4fe012d6b9b7d4`
* `tokenizer.json` (33,384,567 bytes): SHA256=`daab2354f8a74e70d70b4d1f804939b68a8c9624dd06cb7858e52dd8970e9726`
* `README.md` (5,298 bytes): SHA256=`2ce1c8bb9e7fac8febc53e12c329ea89b83c24db0fd38fc750650a71bb6e87f6`
* `adapter_model.safetensors` (131,250,184 bytes): SHA256=`70262714fe6d411787053d629b0f0b3a278f20568a56dc3ef3001c47abfac09b`
* `chat_template.jinja` (1,532 bytes): SHA256=`7de1c58e208eda46e9c7f86397df37ec49883aeece39fb961e0a6b24088dd3c4`
