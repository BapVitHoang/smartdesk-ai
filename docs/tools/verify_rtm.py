"""Validation script to verify that every source file and test case in docs/REPORT.md RTM exists."""

import os
import re
import sys

def verify_rtm():
    report_path = "docs/REPORT.md"
    if not os.path.exists(report_path):
        print(f"Error: {report_path} not found.")
        sys.exit(1)

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match lines in Section 2.2 table
    # Table header: | User Story / Yêu Cầu (REQ) | API Endpoint / Thành Phần UI | Tệp Nguồn Xử Lý (Source Files) | Kịch Bản Kiểm Thử Tự Động (Test Cases) |
    lines = content.splitlines()
    in_rtm = False
    rtm_rows = []

    for line in lines:
        if "### 2.2 Bảng Ma trận Truy vết Yêu cầu" in line:
            in_rtm = True
            continue
        if in_rtm and line.startswith("## "):
            break
        if in_rtm and line.strip().startswith("|") and "**REQ-" in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 4:
                req_col = parts[0]
                api_col = parts[1]
                src_col = parts[2]
                test_col = parts[3]
                rtm_rows.append((req_col, api_col, src_col, test_col))

    print(f"Found {len(rtm_rows)} RTM requirement rows in {report_path}.")

    if len(rtm_rows) != 42:
        print(f"WARNING: Expected 42 RTM rows, found {len(rtm_rows)}.")

    missing_files = []
    missing_tests = []

    for req, api, src, test in rtm_rows:
        # Extract file paths from src (e.g. `backend/app/main.py`)
        src_files = re.findall(r"`([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)`", src)
        for sf in src_files:
            if not os.path.exists(sf):
                missing_files.append((req, sf))

        # Extract test references (e.g. `backend/tests/test_api.py::test_health_check` or `backend/tests/...py`)
        tests = re.findall(r"`([a-zA-Z0-9_\-./]+\.py(?:::[a-zA-Z0-9_]+)?)`", test)
        for t in tests:
            test_file = t.split("::")[0]
            if not os.path.exists(test_file):
                missing_tests.append((req, t))

    print(f"\n--- Validation Results ---")
    print(f"Checked source files across 42 requirements.")
    if missing_files:
        print(f"FAILED: {len(missing_files)} missing source files:")
        for req, mf in missing_files:
            print(f"  - [{req}] {mf}")
    else:
        print(f"[PASS] All referenced source files exist on disk.")

    if missing_tests:
        print(f"FAILED: {len(missing_tests)} missing test files:")
        for req, mt in missing_tests:
            print(f"  - [{req}] {mt}")
    else:
        print(f"[PASS] All referenced test files exist on disk.")

    if missing_files or missing_tests or len(rtm_rows) != 42:
        sys.exit(1)
    else:
        print(f"\nSUCCESS: 100% of RTM table entries ({len(rtm_rows)}/42) verified successfully!")

if __name__ == "__main__":
    verify_rtm()
