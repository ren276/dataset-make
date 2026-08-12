import subprocess
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas.generation_manifest import GenerationManifest

def get_command_output(cmd: list) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
    except Exception as e:
        return f"Error: {str(e)}"

def hash_file(file_path: Path) -> str:
    if not file_path.exists():
        return "none"
    hasher = hashlib.sha256()
    hasher.update(file_path.read_bytes())
    return hasher.hexdigest()

def generate_manifest(v010_dir: Path, output_dir: Path, synthea_root: Path, config_dir: Path, seed: int, pop_size: int):
    dataset_make_git_commit = get_command_output(["git", "rev-parse", "HEAD"])
    
    synthea_commit = "unknown"
    if synthea_root.exists():
        synthea_commit = get_command_output(["git", "-C", str(synthea_root), "rev-parse", "HEAD"])
        if "Error" in synthea_commit:
            synthea_commit = "unknown"
            
    java_version = get_command_output(["java", "-version"])
    gradle_version = get_command_output([str(synthea_root / "gradlew"), "--version"]) if (synthea_root / "gradlew").exists() else "unknown"
    python_version = get_command_output(["python3", "--version"])
    pip_freeze = get_command_output(["python3", "-m", "pip", "freeze"])
    
    # Hash dependencies (requirements.txt if exists, else hash the pip freeze output itself)
    req_file = config_dir.parent.parent / "requirements.txt"
    if req_file.exists():
        dependency_lock_hash = hash_file(req_file)
    else:
        dependency_lock_hash = hashlib.sha256(pip_freeze.encode()).hexdigest()
        
    # Get raw source hashes from v0.1.0
    raw_source_hashes = {}
    v010_csv_dir = v010_dir / "source" / "csv"
    if v010_csv_dir.exists():
        for file_path in sorted(v010_csv_dir.glob("*.csv")):
            if file_path.is_file():
                raw_source_hashes[file_path.name] = hash_file(file_path)
    
    manifest = GenerationManifest(
        dataset_make_git_commit=dataset_make_git_commit,
        synthea_git_commit=synthea_commit,
        java_version=java_version.split('\n')[0] if java_version else "unknown",
        gradle_version=gradle_version.split('\n')[0] if gradle_version else "unknown",
        python_version=python_version,
        pip_freeze=pip_freeze,
        dependency_lock_hash=dependency_lock_hash,
        generation_seed=seed,
        population_size=1140,
        age_range="5-80",
        raw_source_hashes=raw_source_hashes,
        adaptation_config_hash=hash_file(config_dir / "india_geography.yaml"),
        clinical_derivation_rules_hash=hash_file(config_dir / "clinical_derivation_rules.yaml"),
        scenario_rules_hash=hash_file(config_dir / "scenario_rules.yaml"),
        kernel_config_hash=hash_file(config_dir / "kernel_rules.yaml"),
        task_taxonomy_hash=hash_file(config_dir / "condition_presenting_problem_scenarios.yaml"),
        generator_version="v0.1.1",
        schema_version="v0.1.1",
        dataset_version="v0.1.1"
    )
    
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "generation_manifest.json"
    manifest_path.write_text(manifest.to_json())
    print(f"Manifest written to {manifest_path}")
    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--v010-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--synthea-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--pop-size", type=int, required=True)
    
    args = parser.parse_args()
    ok = generate_manifest(args.v010_dir, args.output_dir, args.synthea_root, args.config_dir, args.seed, args.pop_size)
    sys.exit(0 if ok else 1)
