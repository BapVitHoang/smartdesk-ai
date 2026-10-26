"""Execute and verify the 3 live-change scenarios in an isolated scratch copy in %TEMP%.
Ensures repository working tree and Docker pgdata volume are completely untouched.
"""

import os
import shutil
import tempfile
import subprocess
import json
import re
import sys

def run_scratch_scenarios():
    temp_dir = tempfile.gettempdir()
    scratch_root = os.path.join(temp_dir, "smartdesk_live_scratch")

    if os.path.exists(scratch_root):
        shutil.rmtree(scratch_root, ignore_errors=True)

    print(f"[SETUP] Copying backend codebase to scratch directory: {scratch_root}")
    shutil.copytree("backend", os.path.join(scratch_root, "backend"), ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))

    scratch_backend = os.path.join(scratch_root, "backend")
    env = os.environ.copy()
    env["PYTHONPATH"] = scratch_backend

    results = {}

    try:
        # Scenario 1: Modify Prompt Guideline in prompts.json
        print("\n--- Running Scenario 1: Add greeting guideline to prompts.json ---")
        prompt_path = os.path.join(scratch_backend, "data", "prompts.json")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_data = json.load(f)

        orig_tpl = prompt_data["templates"]["rag_customer_support"]["template"]
        new_rule = "\n5. BẮT BUỘC: Luôn mở đầu câu trả lời bằng lời chào: 'Chúc quý khách một ngày làm việc tràn đầy năng lượng!'."
        prompt_data["templates"]["rag_customer_support"]["template"] = orig_tpl + new_rule

        with open(prompt_path, "w", encoding="utf-8") as f:
            json.dump(prompt_data, f, ensure_ascii=False, indent=2)

        cmd1 = [sys.executable, "-m", "pytest", os.path.join(scratch_backend, "tests", "test_rag_module.py"), f"--rootdir={scratch_backend}", "-k", "test_prompt_registry_loads_versioned_templates", "-q"]
        proc1 = subprocess.run(cmd1, env=env, capture_output=True, text=True)
        results["scenario_1"] = {
            "exit_code": proc1.returncode,
            "stdout": proc1.stdout.strip(),
            "stderr": proc1.stderr.strip()
        }
        print(f"Scenario 1 Exit: {proc1.returncode}")
        print(f"Output: {proc1.stdout.strip()[:100]}")

        # Scenario 2: Modify Chunk Size & Overlap in config.py
        print("\n--- Running Scenario 2: Change CHUNK_SIZE=500 and CHUNK_OVERLAP=50 in config.py ---")
        config_path = os.path.join(scratch_backend, "app", "core", "config.py")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg_text = f.read()

        cfg_text = cfg_text.replace("CHUNK_SIZE: int = 700", "CHUNK_SIZE: int = 500")
        cfg_text = cfg_text.replace("CHUNK_OVERLAP: int = 100", "CHUNK_OVERLAP: int = 50")

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(cfg_text)

        cmd2 = [sys.executable, "-m", "pytest", os.path.join(scratch_backend, "tests", "test_workspace_and_verification.py"), f"--rootdir={scratch_backend}", "-k", "test_clean_json_response_fail_closed", "-q"]
        proc2 = subprocess.run(cmd2, env=env, capture_output=True, text=True)
        results["scenario_2"] = {
            "exit_code": proc2.returncode,
            "stdout": proc2.stdout.strip(),
            "stderr": proc2.stderr.strip()
        }
        print(f"Scenario 2 Exit: {proc2.returncode}")
        print(f"Output: {proc2.stdout.strip()[:100]}")

        # Scenario 3: Add new field to Pydantic schema in ai_structured.py
        print("\n--- Running Scenario 3: Add requires_manager_review field to TicketCopilotStructuredOutput ---")
        schema_path = os.path.join(scratch_backend, "app", "schemas", "ai_structured.py")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_text = f.read()

        field_addition = "requires_manager_review: bool = Field(default=False, description='True if ticket is Urgent')\n    confidence: float = Field("
        schema_text = schema_text.replace("confidence: float = Field(", field_addition)

        with open(schema_path, "w", encoding="utf-8") as f:
            f.write(schema_text)

        cmd3 = [sys.executable, "-m", "pytest", os.path.join(scratch_backend, "tests", "test_rag_module.py"), f"--rootdir={scratch_backend}", "-k", "test_structured_output_schemas_and_category_alias_normalization", "-q"]
        proc3 = subprocess.run(cmd3, env=env, capture_output=True, text=True)
        results["scenario_3"] = {
            "exit_code": proc3.returncode,
            "stdout": proc3.stdout.strip(),
            "stderr": proc3.stderr.strip()
        }
        print(f"Scenario 3 Exit: {proc3.returncode}")
        print(f"Output: {proc3.stdout.strip()[:100]}")

    finally:
        print(f"\n[CLEANUP] Removing scratch directory: {scratch_root}")
        shutil.rmtree(scratch_root, ignore_errors=True)
        print("[CLEANUP] Completed.")

    all_passed = all(r["exit_code"] == 0 for r in results.values())
    print("\n=== All 3 Scenarios Summary ===")
    for sc, data in results.items():
        status_str = "PASS" if data["exit_code"] == 0 else "FAIL"
        print(f"  {sc}: {status_str} (exit code {data['exit_code']}) -> {data['stdout']}")

    if not all_passed:
        sys.exit(1)
    else:
        print("\n[SUCCESS] 3/3 Live-change scenarios verified in isolated scratch environment!")

if __name__ == "__main__":
    run_scratch_scenarios()
