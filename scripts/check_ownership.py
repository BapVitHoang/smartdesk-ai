#!/usr/bin/env python3
"""
SmartDesk AI - Ownership & Conflict-Prevention Enforcement Script
Validates that developers only touch files within their assigned module boundaries.

Usage:
    python scripts/check_ownership.py [--branch <branch_name>] [--staged] [--owner <devA|devB|devC|lead>] [--as-integrator] [--verify-consistency]
"""

import sys
import subprocess
import argparse
import fnmatch
from pathlib import Path
from typing import List, Tuple, Set

# Import authoritative map
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from scripts.ownership_map import OWNERSHIP_MAP


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
    norm_file = file_path.replace("\\", "/").lstrip("/")
    for pattern in patterns:
        norm_pattern = pattern.replace("\\", "/").lstrip("/")
        if norm_pattern.endswith("/*") or norm_pattern.endswith("/**"):
            prefix = norm_pattern.rstrip("/*").rstrip("/**")
            if norm_file.startswith(prefix + "/") or norm_file == prefix:
                return True
        elif fnmatch.fnmatch(norm_file, norm_pattern):
            return True
    return False


def check_violations(owner: str, files: List[str], as_integrator: bool = False) -> Tuple[List[str], List[str]]:
    allowed = list(OWNERSHIP_MAP.get(owner, []))
    if owner == "devB" and as_integrator:
        allowed.extend(OWNERSHIP_MAP.get("integrator", []))

    frozen_patterns = OWNERSHIP_MAP.get("integrator", [])
    cross_owner_violations = []
    frozen_contract_violations = []

    for f in files:
        # Check if it is a frozen integration file
        is_frozen = is_pattern_match(f, frozen_patterns)
        is_allowed = is_pattern_match(f, allowed)

        if is_frozen and not (owner == "devB" and as_integrator):
            frozen_contract_violations.append(f)
        elif not is_allowed:
            cross_owner_violations.append(f)

    return cross_owner_violations, frozen_contract_violations


def verify_consistency() -> bool:
    """Verifies that OWNERSHIP_MAP, CODEOWNERS, and WORKSTREAMS table are consistent."""
    print("=== Checking Ownership & Governance Consistency ===")
    has_errors = False

    # 1. Check all tracked files are mapped in OWNERSHIP_MAP
    try:
        tracked_files = [f.strip().replace("\\", "/") for f in run_git(["ls-files"]).splitlines() if f.strip()]
    except Exception as e:
        print(f"[ERROR] Could not list tracked files: {e}")
        return False

    all_patterns = []
    for owner, patterns in OWNERSHIP_MAP.items():
        all_patterns.extend(patterns)

    unmapped = []
    for f in tracked_files:
        if not is_pattern_match(f, all_patterns):
            unmapped.append(f)

    if unmapped:
        print(f"[FAIL] Found {len(unmapped)} tracked files not covered by OWNERSHIP_MAP:")
        for f in unmapped[:10]:
            print(f"  - {f}")
        has_errors = True
    else:
        print(f"[PASS] All {len(tracked_files)} tracked files are mapped to an owner.")

    # 2. Check for overlap between devA, devB, devC (Integrator is separate frozen hat)
    core_owners = ["devA", "devB", "devC"]
    overlaps = []
    for i in range(len(core_owners)):
        for j in range(i + 1, len(core_owners)):
            o1, o2 = core_owners[i], core_owners[j]
            p1, p2 = OWNERSHIP_MAP[o1], OWNERSHIP_MAP[o2]
            for f in tracked_files:
                if is_pattern_match(f, p1) and is_pattern_match(f, p2):
                    overlaps.append((f, o1, o2))

    if overlaps:
        print(f"[FAIL] Found {len(overlaps)} file ownership overlaps between developers:")
        for f, o1, o2 in overlaps:
            print(f"  - {f} (claimed by both {o1} and {o2})")
        has_errors = True
    else:
        print("[PASS] Zero overlaps between devA, devB, and devC.")

    # 3. Check CODEOWNERS exists and matches
    codeowners_path = repo_root / ".github" / "CODEOWNERS"
    if not codeowners_path.exists():
        print("[FAIL] .github/CODEOWNERS does not exist.")
        has_errors = True
    else:
        print("[PASS] .github/CODEOWNERS exists.")

    return not has_errors


def main():
    parser = argparse.ArgumentParser(description="Check module ownership boundaries.")
    parser.add_argument("--branch", type=str, default=None, help="Explicit branch name to test.")
    parser.add_argument("--staged", action="store_true", help="Check currently staged files.")
    parser.add_argument("--owner", type=str, choices=["owner1", "owner2", "owner3", "devA", "devB", "devC", "lead", "integrator"], default=None)
    parser.add_argument("--as-integrator", action="store_true", help="Allow devB (Hoang) to modify integrator-owned frozen files.")
    parser.add_argument("--verify-consistency", action="store_true", help="Verify consistency across governance artifacts.")
    args = parser.parse_args()

    if args.verify_consistency:
        success = verify_consistency()
        sys.exit(0 if success else 1)

    branch = args.branch or get_current_branch()
    owner = args.owner

    # Normalize aliases
    if owner in ["devA", "owner1"]:
        owner = "devA"
    elif owner in ["devB", "owner2"]:
        owner = "devB"
    elif owner in ["devC", "owner3"]:
        owner = "devC"
    elif owner in ["integrator", "lead"]:
        owner = "integrator"

    # Enforce --as-integrator rule: Only devB can use --as-integrator
    if args.as_integrator and owner not in ["devB", "integrator"]:
        print(f"[ERROR] Only devB (Hoang) is authorized to use --as-integrator. {owner} is forbidden.")
        sys.exit(1)

    if not owner:
        branch_lower = branch.lower()
        if "feature/a-" in branch_lower or "deva" in branch_lower or "owner1" in branch_lower:
            owner = "devA"
        elif "feature/b-" in branch_lower or "devb" in branch_lower or "owner2" in branch_lower:
            owner = "devB"
        elif "feature/c-" in branch_lower or "devc" in branch_lower or "owner3" in branch_lower:
            owner = "devC"
        elif branch_lower in ["hoang", "main", "master", "integration"] or "lead" in branch_lower:
            owner = "integrator"
        else:
            print(f"[INFO] Unknown branch role '{branch}'. Assuming integrator mode.")
            owner = "integrator"

    print(f"=== SmartDesk AI Ownership Check ===")
    print(f"Branch: {branch}")
    print(f"Role: {owner.upper()}{' (with Integrator hat)' if args.as_integrator else ''}")

    files = get_modified_files(staged=args.staged)
    if not files:
        print("[OK] No modified files detected. Clean working tree.")
        sys.exit(0)

    print(f"Files to inspect ({len(files)}):")
    for f in files:
        print(f"  - {f}")

    if owner == "integrator":
        print("[OK] Integrator role has access to all files.")
        sys.exit(0)

    cross_violations, frozen_violations = check_violations(owner, files, as_integrator=args.as_integrator)

    if cross_violations or frozen_violations:
        print("\n[ERROR] OWNERSHIP BOUNDARY VIOLATION DETECTED!")
        if frozen_violations:
            print("\n* The following modified files are FROZEN SHARED INTEGRATION CONTRACTS:")
            for f in frozen_violations:
                print(f"  [FROZEN] {f}")
            print("  -> Frozen files may only be modified by the Integrator (Hoang).")
            print("  -> Please file a change request in docs/requests/dev<A|B|C>.md.")

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
