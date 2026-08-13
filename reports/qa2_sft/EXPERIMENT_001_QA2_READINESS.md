# PHC SaMD Experiment 001-QA2: SFT Readiness Status

```text
GOOGLE_REFERENCE:
VERIFIED

DATASET:
FROZEN_AND_READY

ENVIRONMENT:
READY

TRAINING_CONFIGURATION:
EXPERIMENT_001_QA2_FINAL

FULL_SFT:
NOT_STARTED
```

---

## Final Decision Summary

$$\mathbf{FINAL\ DECISION:\ READY\_FOR\_EXPERIMENT\_001\_QA2\_SFT}$$

### Verification Checklist
1. **QLoRA NF4 Memory Execution:** Successfully executed 1-step forward + backward + optimizer pass (`ENVIRONMENT_VALIDATION_ONLY`). Measured peak VRAM is **9.34 GB**, leaving **6.22 GB of headroom (40.0% safety margin)** on the 15.56 GB GPU.
2. **Reproducibility:** Peak VRAM is 100% identical across 2 consecutive validation runs (9.34 GB).
3. **Dataset Length Analysis:** 100.0% of records in the frozen release fit within `max_length=512` (P100 max record length is 489 tokens). Zero truncation occurs.
4. **Loss Masking:** Assistant-only loss verified under QLoRA 4-bit NF4 (`SFTConfig(assistant_only_loss=True)`). System/user tokens masked, assistant target and EOS sequence (`<end_of_turn>\n`) active.
5. **Frozen Base Model:** Base model weights in 4-bit NF4 quantized format with `requires_grad=False`. Only 32,788,480 LoRA adapter parameters (1.300%) are trainable.
6. **Frozen Dataset:** Dataset `longitudinal_data/v0.1.3-QA.1.1/` remains byte-for-byte unmodified.
7. **Full SFT Status:** Full SFT has **NOT** been started. No training checkpoints created.
