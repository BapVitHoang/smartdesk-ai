#!/usr/bin/env python3
"""
SmartDesk AI - Ownership & Conflict-Prevention Enforcement Script
Validates that developers only touch files within their assigned module boundaries.

Usage:
    python scripts/check_ownership.py [--branch <branch_name>] [--staged]
"""

import sys
import subprocess
import argparse
import fnmatch
from typing import List, Tuple

# Module Ownership Mapping
OWNER_PATTERNS = {
    "owner1": [
        "backend/app/services/rag_service.py",
        "backend/app/services/llm_service.py",
        "backend/app/services/embedding_service.py",
        "backend/app/services/fallback_service.py",
        "backend/app/services/verification_service.py",
        "backend/app/services/agent_tools.py",
        "backend/app/services/ai_usage_logger.py",
        "backend/app/core/prompts.py",
        "backend/app/core/security.py",
        "backend/app/schemas/ai_structured.py",
        "backend/app/api/v1/endpoints/chat.py",
        "backend/app/api/v1/endpoints/chat_stream.py",
        "backend/app/api/v1/endpoints/chat_actions.py",
        "backend/app/api/v1/endpoints/ai_usage.py",
        "backend/tests/test_rag_module.py",
        "backend/tests/test_ollama_provider.py",
        "backend/tests/test_eval_cases.py",
        "backend/data/prompts.json",
        "backend/data/seed_faq.json",
        "frontend/src/features/chat/*",
        "frontend/src/features/telemetry/*",
        "frontend/src/services/api/chat.ts",
        "frontend/src/services/api/telemetry.ts",
    ],
    "owner2": [
        "backend/app/services/ticket_service.py",
        "backend/app/services/document_service.py",
        "backend/app/db/session.py",
        "backend/app/db/base.py",
        "backend/app/db/seed/*",
        "backend/app/models/*",
        "backend/app/core/deps.py",
        "backend/app/api/v1/endpoints/tickets.py",
        "backend/app/api/v1/endpoints/agent.py",
        "backend/app/api/v1/endpoints/workspaces.py",
        "backend/app/api/v1/endpoints/documents.py",
        "backend/app/api/v1/endpoints/auth.py",
        "backend/app/api/v1/endpoints/health.py",
        "backend/tests/test_tickets_module.py",
        "backend/tests/test_auth_module.py",
        "backend/tests/test_workspace_and_verification.py",
        "frontend/src/features/agent/*",
        "frontend/src/features/auth/*",
        "frontend/src/features/knowledge/*",
        "frontend/src/services/api/tickets.ts",
        "frontend/src/services/api/workspaces.ts",
        "frontend/src/services/api/documents.ts",
        "frontend/src/services/api/auth.ts",
    ],
    "owner3": [
        "frontend/src/components/*",
        "frontend/src/App.tsx",
        "frontend/src/main.tsx",
        "frontend/src/data.ts",
        "frontend/src/services/mocks/*",
        "docker-compose.yml",
        "Dockerfile*",
        "scripts/*",
        ".github/workflows/*",
        "docs/*",
    ],
}

FROZEN_SHARED_FILES = [
    "backend/app/api/v1/api.py",
    "backend/app/core/config.py",
    "backend/app/main.py",
    "frontend/src/types.ts",
    "frontend/src/types/*",
    "frontend/src/services/api.ts",
    "frontend/src/services/api/client.ts",
    "frontend/src/services/api/index.ts",
    "docs/API_CONTRACT.md",
    "docs/spec/CONTRACTS.md",
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
    for pattern in patterns:
        norm_pattern = pattern.replace("\\", "/")
        if norm_pattern.endswith("/*"):
            prefix = norm_pattern[:-2]
            if file_path.startswith(prefix + "/") or file_path == prefix:
                return True
        elif fnmatch.fnmatch(file_path, norm_pattern):
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
    parser.add_argument("--owner", type=str, choices=["owner1", "owner2", "owner3", "lead"], default=None)
    args = parser.parse_args()

    branch = args.branch or get_current_branch()
    owner = args.owner

    if not owner:
        branch_lower = branch.lower()
        if "owner1" in branch_lower or "ai" in branch_lower or "rag" in branch_lower:
            owner = "owner1"
        elif "owner2" in branch_lower or "platform" in branch_lower or "ticket" in branch_lower:
            owner = "owner2"
        elif "owner3" in branch_lower or "ux" in branch_lower or "qa" in branch_lower or "devops" in branch_lower:
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
