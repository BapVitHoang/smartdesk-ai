#!/usr/bin/env python3
"""
SmartDesk AI - Ownership & Conflict-Prevention Enforcement Script
Validates that developers only touch files within their assigned module boundaries.

Usage:
    python scripts/check_ownership.py [--branch <branch_name>] [--staged] [--owner <owner1|owner2|owner3|lead>]
"""

import sys
import subprocess
import argparse
import fnmatch
from typing import List, Tuple

# Module Ownership Mapping
OWNER_PATTERNS = {
    "owner1": [
        "backend/app/services/llm_service.py",
        "backend/app/services/rag_service.py",
        "backend/app/services/ticket_copilot_service.py",
        "backend/app/services/fallback_service.py",
        "backend/app/services/verification_service.py",
        "backend/app/services/agent_tools.py",
        "backend/app/core/prompts.py",
        "backend/app/schemas/ai_structured.py",
        "backend/app/schemas/chat.py",
        "backend/app/schemas/verification.py",
        "backend/app/schemas/ai_usage.py",
        "backend/app/api/v1/endpoints/chat.py",
        "backend/app/api/v1/endpoints/chat_stream.py",
        "backend/app/api/v1/endpoints/chat_actions.py",
        "backend/app/api/v1/endpoints/ai_usage.py",
        "backend/app/api/v1/endpoints/knowledge.py",
        "backend/data/prompts.json",
        "backend/data/seed_faq.json",
        "backend/data/finetune_alpaca.jsonl",
        "backend/data/sample_documents/*",
        "backend/data/eval_dataset.json",
        "backend/scripts/run_eval.py",
        "backend/scripts/reembed_chunks.py",
        "backend/scripts/export_finetune_dataset.py",
        "Modelfile",
        "backend/tests/test_rag_module.py",
        "backend/tests/test_ollama_provider.py",
        "backend/tests/ai/*",
        "docs/notes/A.md",
        "docs/notes/A-ai-usage.md",
        "docs/requests/A.md",
        "docs/requests/devA.md",
    ],
    "owner2": [
        "backend/app/services/ticket_service.py",
        "backend/app/services/document_service.py",
        "backend/app/services/embedding_service.py",
        "backend/app/services/ai_usage_logger.py",
        "backend/app/core/deps.py",
        "backend/app/core/security.py",
        "backend/app/db/base.py",
        "backend/app/db/session.py",
        "backend/app/db/seed/*",
        "backend/app/models/ai_usage.py",
        "backend/app/models/document.py",
        "backend/app/models/knowledge.py",
        "backend/app/models/ticket.py",
        "backend/app/models/user.py",
        "backend/app/models/verification.py",
        "backend/app/models/workspace.py",
        "backend/app/schemas/ticket.py",
        "backend/app/schemas/workspace.py",
        "backend/app/schemas/document.py",
        "backend/app/schemas/auth.py",
        "backend/app/api/v1/endpoints/auth.py",
        "backend/app/api/v1/endpoints/tickets.py",
        "backend/app/api/v1/endpoints/agent.py",
        "backend/app/api/v1/endpoints/workspaces.py",
        "backend/app/api/v1/endpoints/documents.py",
        "backend/app/api/v1/endpoints/health.py",
        "backend/tests/test_tickets_module.py",
        "backend/tests/test_auth_module.py",
        "backend/tests/test_workspace_and_verification.py",
        "backend/tests/platform/*",
        "docker-compose.yml",
        "docs/notes/B.md",
        "docs/notes/B-ai-usage.md",
        "docs/requests/B.md",
        "docs/requests/devB.md",
    ],
    "owner3": [
        "frontend/src/*",
        "frontend/Dockerfile",
        "frontend/nginx.conf",
        "frontend/index.html",
        "frontend/metadata.json",
        "backend/Dockerfile",
        "backend/PYTHON_FILES_EXPLANATION.md",
        "backend/README.md",
        "backend/tests/test_api.py",
        "backend/tests/common/*",
        "README.md",
        "AI_USAGE.md",
        "docs/DESIGN.md",
        "docs/PROPOSAL.md",
        "docs/TEST_ACCEPTANCE.md",
        "docs/REPORT.md",
        "docs/PRESENTATION_AND_DEMO.md",
        "docs/EVALUATION_REPORT.md",
        "docs/adr/*",
        "docs/audit/*",
        "docs/notes/*",
        "docs/requests/C.md",
        "docs/requests/devC.md",
        "scripts/install.bat",
        "scripts/start.bat",
        "scripts/start_all.bat",
        "scripts/start_backend.bat",
    ],
}

FROZEN_SHARED_FILES = [
    "backend/app/core/config.py",
    "backend/app/core/exceptions.py",
    "backend/requirements.txt",
    "backend/.env.example",
    "backend/app/api/v1/api.py",
    "backend/app/models/__init__.py",
    "backend/app/schemas/__init__.py",
    "backend/app/__init__.py",
    "backend/app/api/__init__.py",
    "backend/app/api/v1/__init__.py",
    "backend/app/core/__init__.py",
    "backend/app/db/__init__.py",
    "backend/app/services/__init__.py",
    "backend/tests/__init__.py",
    "backend/tests/conftest.py",
    "docs/spec/CONTRACTS.md",
    "docs/API_CONTRACT.md",
    "AGENTS.md",
    ".cursorrules",
    ".gitattributes",
    ".gitignore",
    "pytest.ini",
    "smartdesk_audit_report.md",
    "frontend/.env.example",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
    "frontend/src/types.ts",
    "frontend/src/types/index.ts",
    "frontend/src/services/api.ts",
    "frontend/src/services/api/index.ts",
    "frontend/src/services/api/client.ts",
]


def run_git(args: List[str]) -> str:
    res = subprocess.run(["git"] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return res.stdout.strip()


def get_current_branch() -> str:
    try:
        return run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    except Exception:
        return "unknown"


def get_modified_files(staged: bool = False, base_branch: str = "origin/Hoang") -> List[str]:
    try:
        if staged:
            out = run_git(["diff", "--cached", "--name-only"])
        else:
            out = run_git(["diff", "--name-only", base_branch])
        if not out:
            return []
        return [f.strip().replace("\\", "/") for f in out.splitlines() if f.strip()]
    except Exception as e:
        print(f"[WARN] Failed to get git diff: {e}")
        return []


def is_pattern_match(file_path: str, patterns: List[str]) -> bool:
    norm_file = file_path.replace("\\", "/")
    for pattern in patterns:
        norm_pattern = pattern.replace("\\", "/")
        if norm_pattern.endswith("/*"):
            prefix = norm_pattern[:-2]
            if norm_file.startswith(prefix + "/") or norm_file == prefix:
                return True
        elif fnmatch.fnmatch(norm_file, norm_pattern):
            return True
    return False


def check_violations(owner: str, files: List[str]) -> Tuple[List[str], List[str]]:
    allowed = OWNER_PATTERNS.get(owner, [])
    cross_owner_violations = []
    frozen_contract_violations = []

    for f in files:
        # Check frozen integration contract
        if is_pattern_match(f, FROZEN_SHARED_FILES):
            frozen_contract_violations.append(f)
            continue

        # Check if allowed in owner's lane
        if not is_pattern_match(f, allowed):
            cross_owner_violations.append(f)

    return cross_owner_violations, frozen_contract_violations


def main():
    parser = argparse.ArgumentParser(description="Check module ownership boundaries.")
    parser.add_argument("--branch", type=str, default=None, help="Explicit branch name to test.")
    parser.add_argument("--staged", action="store_true", help="Check currently staged files.")
    parser.add_argument("--owner", type=str, choices=["owner1", "owner2", "owner3", "devA", "devB", "devC", "lead"], default=None)
    args = parser.parse_args()

    branch = args.branch or get_current_branch()
    owner = args.owner

    # Normalize aliases
    if owner == "devA":
        owner = "owner1"
    elif owner == "devB":
        owner = "owner2"
    elif owner == "devC":
        owner = "owner3"

    if not owner:
        branch_lower = branch.lower()
        if "feature/a-" in branch_lower or "deva" in branch_lower or "owner1" in branch_lower:
            owner = "owner1"
        elif "feature/b-" in branch_lower or "devb" in branch_lower or "owner2" in branch_lower:
            owner = "owner2"
        elif "feature/c-" in branch_lower or "devc" in branch_lower or "owner3" in branch_lower:
            owner = "owner3"
        elif branch_lower in ["hoang", "main", "master", "integration"] or "lead" in branch_lower:
            owner = "lead"
        else:
            print(f"[INFO] Unknown branch role '{branch}'. Assuming lead / integration mode.")
            owner = "lead"

    print(f"=== SmartDesk AI Ownership Check ===")
    print(f"Branch: {branch}")
    print(f"Role: {owner.upper()}")

    files = get_modified_files(staged=args.staged)
    if not files:
        print("[OK] No modified files detected. Clean working tree.")
        sys.exit(0)

    print(f"Files to inspect ({len(files)}):")
    for f in files:
        print(f"  - {f}")

    if owner == "lead":
        print("[OK] Lead/Integration role has access to all files.")
        sys.exit(0)

    cross_violations, frozen_violations = check_violations(owner, files)

    if cross_violations or frozen_violations:
        print("\n[ERROR] OWNERSHIP BOUNDARY VIOLATION DETECTED!")
        if frozen_violations:
            print("\n* The following modified files are FROZEN SHARED INTEGRATION CONTRACTS:")
            for f in frozen_violations:
                print(f"  [FROZEN] {f}")
            print("  -> Frozen files may only be modified by the Integration Owner.")
            print("  -> Please file a change request in docs/requests/<your_name>.md.")

        if cross_violations:
            print("\n* The following modified files belong to ANOTHER MODULE OWNER:")
            for f in cross_violations:
                print(f"  [CROSS-OWNER] {f}")
            print(f"  -> {owner.upper()} is not permitted to edit files outside their module boundary.")

        print("\nPlease revert changes to unauthorized files before pushing.")
        sys.exit(1)

    print("\n[OK] All modified files conform to module ownership boundaries!")
    sys.exit(0)


if __name__ == "__main__":
    main()
