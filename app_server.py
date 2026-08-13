import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import time
import json
import torch
import psutil
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

REPO_ROOT = Path(__file__).resolve().parent
MODEL_PATH = Path("/media/acps/twoTBDrive/SandeshWork/AI/medgemma/models/medgemma-1.5-4b-it")
ADAPTER_PATH = REPO_ROOT / "experiment_001_qa2_output/final_adapter"
RESEARCH_UI_DIR = REPO_ROOT / "research_ui"

app = FastAPI(
    title="PHC SaMD MedGemma 1.5 4B IT Research Inference Service",
    version="0.1.0-qa7",
    description="Local Research Inference API & Decoupled Browser Chat UI"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading MedGemma Tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print("Loading MedGemma 1.5 4B IT Base Model in 4-bit NF4...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16
)

base_model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.bfloat16
)

print("Loading Frozen PHC LoRA Adapter...")
model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
model.eval()

print("MedGemma Research Service Ready!")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    system_prompt: Optional[str] = None

@app.get("/health")
def health():
    return {
        "status": "HEALTHY",
        "model_loaded": True,
        "gpu_available": torch.cuda.is_available(),
        "vram_allocated_gb": round(torch.cuda.memory_allocated() / (1024**3), 2)
    }

@app.get("/v1/model-info")
def model_info():
    return {
        "base_model": "google/medgemma-1.5-4b-it",
        "base_revision": "91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b",
        "adapter_path": str(ADAPTER_PATH),
        "adapter_sha256": "70262714fe6d411787053d629b0f0b3a278f20568a56dc3ef3001c47abfac09b",
        "gpu": torch.cuda.get_device_name(0),
        "quantization": "4bit_nf4",
        "max_input_length": 576,
        "max_new_tokens": 256
    }

def sanitize_and_truncate_history(messages, default_system, max_len=576):
    sys_prompt = default_system
    dialog = []
    
    for m in messages:
        role_val = m.role if hasattr(m, 'role') else m['role']
        content_val = m.content if hasattr(m, 'content') else m['content']
        if role_val == "system":
            sys_prompt = content_val
        else:
            role = "user" if role_val not in ["user", "assistant"] else role_val
            dialog.append({"role": role, "content": content_val})
            
    # Combine consecutive messages from same role
    clean_dialog = []
    for m in dialog:
        if clean_dialog and clean_dialog[-1]["role"] == m["role"]:
            clean_dialog[-1]["content"] += "\n" + m["content"]
        else:
            clean_dialog.append(dict(m))
            
    # Truncate oldest turns if token count exceeds max_len (sliding window)
    while len(clean_dialog) > 1:
        test_messages = [{"role": "system", "content": sys_prompt}] + clean_dialog
        test_prompt = tokenizer.apply_chat_template(test_messages, tokenize=False, add_generation_prompt=True)
        tokens = tokenizer(test_prompt, return_tensors="pt").input_ids.shape[1]
        if tokens <= max_len:
            break
        # Drop oldest turn
        clean_dialog.pop(0)
        # Ensure dialog starts with user
        while clean_dialog and clean_dialog[0]["role"] != "user":
            clean_dialog.pop(0)
            
    if not clean_dialog:
        clean_dialog = [{"role": "user", "content": "Hello"}]
    elif clean_dialog[-1]["role"] != "user":
        clean_dialog.append({"role": "user", "content": "Please continue."})
        
    final_messages = [{"role": "system", "content": sys_prompt}] + clean_dialog
    return final_messages

@app.post("/v1/chat")
def chat(req: ChatRequest):
    t_start = time.time()
    
    default_sys = (
        "You are a clinical record explanation assistant.\n"
        "Use only the information provided.\n"
        "Do not invent clinical facts.\n"
        "Do not prescribe.\n"
        "If required information is absent, state that it is not recorded."
    )
    
    sanitized_messages = sanitize_and_truncate_history(req.messages, req.system_prompt or default_sys, max_len=576)

    try:
        prompt_text = tokenizer.apply_chat_template(sanitized_messages, tokenize=False, add_generation_prompt=True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Chat template rendering error: {str(e)}"
        )
        
    inputs = tokenizer(prompt_text, return_tensors="pt").to("cuda")
    input_token_count = inputs.input_ids.shape[1]

    if input_token_count > 576:
        raise HTTPException(
            status_code=400,
            detail=f"Single message context length violation: Input tokens ({input_token_count}) exceed max_input_length (576)."
        )

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id
        )

    gen_tokens = outputs[0][input_token_count:]
    output_token_count = len(gen_tokens)
    gen_text = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
    latency_sec = round(time.time() - t_start, 3)

    return {
        "response": gen_text,
        "model": "medgemma-1.5-4b-phc",
        "inference": {
            "input_tokens": input_token_count,
            "output_tokens": output_token_count,
            "latency_seconds": latency_sec,
            "tokens_per_second": round(output_token_count / max(latency_sec, 0.001), 1)
        }
    }

# Mount static research_ui directory at root
if RESEARCH_UI_DIR.exists():
    app.mount("/", StaticFiles(directory=str(RESEARCH_UI_DIR), html=True), name="static")
