"""
drishti_pipeline/step1_generate.py
===================================
Wraps a single Synthea run for India vitals generation.

Actions:
  1. Backs up the original Synthea biometrics.yml
  2. Copies the India-calibrated biometrics.yml override into place
  3. Invokes Synthea via gradlew.bat with the provided seed and population
  4. Restores the original biometrics.yml
  5. Verifies that observations.csv was produced

Usage (direct):
  python step1_generate.py --seed 42 --pop 500

Called by run_pipeline.py with seed and pop_size args.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Allow running from either inside or outside drishti_pipeline/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drishti_pipeline import config

import os
GRADLEW = config.SYNTHEA_ROOT / ("gradlew.bat" if os.name == 'nt' else "gradlew")


def backup_biometrics():
    """Copy the original biometrics.yml to the backup path (once only)."""
    src = config.SYNTHEA_BIOMETRICS
    bak = config.SYNTHEA_BIOMETRICS_BACKUP
    if not bak.exists():
        shutil.copy2(src, bak)
        print(f"  [step1] Backed up biometrics.yml -> {bak.name}")
    else:
        print(f"  [step1] Backup already exists at {bak.name}, skipping.")


def install_india_biometrics():
    """Replace Synthea biometrics.yml with the India override."""
    shutil.copy2(config.INDIA_BIOMETRICS_SRC, config.SYNTHEA_BIOMETRICS)
    print(f"  [step1] India biometrics.yml installed.")


def restore_biometrics():
    """Restore the original biometrics.yml from backup."""
    bak = config.SYNTHEA_BIOMETRICS_BACKUP
    if bak.exists():
        shutil.copy2(bak, config.SYNTHEA_BIOMETRICS)
        print(f"  [step1] Original biometrics.yml restored.")
    else:
        print(f"  [step1] WARNING: No backup found at {bak}. Cannot restore.", file=sys.stderr)


def run_synthea(seed: int, pop_size: int) -> bool:
    """
    Invoke Synthea via gradlew.bat.
    Returns True on success, False on failure.

    Windows Gradle invocation uses Groovy list syntax:
      gradlew.bat run -Params="['-s','42','-p','300','-a','5-80','-c','path']"
    This matches how run_synthea.bat constructs the command on Windows.
    """
    age_range = f"{config.MIN_AGE}-{config.MAX_AGE}"
    # Properties path with forward slashes (Gradle/Groovy cross-platform)
    props_path = str(config.SYNTHEA_RUN_PROPS).replace("\\", "/")

    # Windows Gradle requires Groovy list syntax for -Params
    # e.g.: -Params="['-s','42','-p','300','-a','5-80','-c','/path/to/props']"
    raw_args = ["-s", str(seed), "-p", str(pop_size), "-a", age_range, "-c", props_path]
    q = "'"
    params_str = "[" + ",".join(f"{q}{a}{q}" for a in raw_args) + "]"
    cmd = [str(GRADLEW), "run", f"-Params={params_str}"]

    print(f"  [step1] Running Synthea: seed={seed}, pop={pop_size}, age={age_range}")
    print(f"  [step1] Params: {params_str}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(config.SYNTHEA_ROOT),
            capture_output=False,   # let Gradle output flow to console
            text=True,
            timeout=600,            # 10 min hard cap
        )
        if result.returncode != 0:
            print(f"  [step1] ERROR: Synthea exited with code {result.returncode}", file=sys.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        print("  [step1] ERROR: Synthea timed out after 10 minutes.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  [step1] ERROR: {e}", file=sys.stderr)
        return False


def verify_output() -> bool:
    """Check that observations.csv was created in the expected output directory."""
    obs_path = config.SYNTHEA_OUTPUT_DIR / "observations.csv"
    patients_path = config.SYNTHEA_OUTPUT_DIR / "patients.csv"
    if not obs_path.exists():
        print(f"  [step1] ERROR: observations.csv not found at {obs_path}", file=sys.stderr)
        return False
    if not patients_path.exists():
        print(f"  [step1] ERROR: patients.csv not found at {patients_path}", file=sys.stderr)
        return False
    obs_size = obs_path.stat().st_size
    print(f"  [step1] observations.csv found ({obs_size:,} bytes). Output OK.")
    return True


def run(seed: int, pop_size: int) -> bool:
    """
    Full step1 execution: backup -> install -> generate -> restore -> verify.
    Returns True if Synthea ran successfully and output is present.
    """
    backup_biometrics()
    install_india_biometrics()
    try:
        success = run_synthea(seed, pop_size)
    finally:
        restore_biometrics()  # always restore, even on failure

    if not success:
        return False
    return verify_output()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 1: Synthea India vitals generation")
    parser.add_argument("--seed",  type=int, required=True, help="Random seed")
    parser.add_argument("--pop",   type=int, default=500,   help="Population size per run")
    args = parser.parse_args()

    ok = run(seed=args.seed, pop_size=args.pop)
    sys.exit(0 if ok else 1)
