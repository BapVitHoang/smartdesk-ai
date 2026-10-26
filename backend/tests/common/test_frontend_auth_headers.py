"""
Offline guard test: verifies that frontend API service functions calling protected
endpoints attach authentication headers (getAuthHeaders) and properly propagate
authentication/authorization errors (ApiError).

Source of protected routes:
- docs/spec/CONTRACTS.md §8.8, §8.9, §8.10, §8.11, §8.12
- docs/API_CONTRACT.md §5, §6, §7
"""

import os
import re
from pathlib import Path
import pytest

FRONTEND_SERVICES_DIR = Path(__file__).resolve().parents[3] / "frontend" / "src" / "services" / "api"

# Protected routes contract table
# (function_name, relative_file, http_method, route_pattern, contracts_section, allow_content_type)
PROTECTED_FRONTEND_FUNCTIONS = [
    # MRG-DEF-03: tickets.ts
    ("updateTicketStatus", "tickets.ts", "PATCH", "/tickets/", "CONTRACTS.md §8.11 (require_role('admin'))", True),
    ("regenerateAiDraft", "tickets.ts", "POST", "/agent/tickets/", "CONTRACTS.md §8.11 (require_role('admin'))", True),
    # MRG-DEF-04: documents.ts
    ("uploadDocument", "documents.ts", "POST", "/documents/upload", "CONTRACTS.md §8.12 (Admin Knowledge Ingestion)", False),
    ("deleteDocument", "documents.ts", "DELETE", "/documents/", "CONTRACTS.md §8.12 (require_role('admin'))", False),
    ("verifyDocument", "documents.ts", "POST", "/verify", "CONTRACTS.md §8.12 (Active Verification Studio)", True),
    ("publishDocument", "documents.ts", "POST", "/publish", "CONTRACTS.md §8.12 (Publish to Live RAG)", True),
    # MRG-DEF-05: workspaces.ts
    ("createWorkspace", "workspaces.ts", "POST", "/workspaces", "CONTRACTS.md §8.12 (Workspace Creation)", True),
    ("updateWorkspace", "workspaces.ts", "PUT", "/workspaces/", "CONTRACTS.md §8.12 (Workspace Update)", True),
]


def extract_function_body(file_content: str, func_name: str) -> str:
    """Extracts the entire body of an exported async function from TS source."""
    # Matches: export async function func_name(...) ... { ... }
    pattern = rf"export\s+async\s+function\s+{func_name}\b[^{{]*\{{"
    match = re.search(pattern, file_content)
    if not match:
        raise ValueError(f"Function {func_name} not found in source file.")
    
    start_pos = match.end() - 1
    depth = 0
    end_pos = start_pos
    for i in range(start_pos, len(file_content)):
        char = file_content[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end_pos = i + 1
                break
    return file_content[start_pos:end_pos]


@pytest.mark.parametrize(
    "func_name,file_name,http_method,route_pattern,contract_ref,allow_content_type",
    PROTECTED_FRONTEND_FUNCTIONS,
)
def test_protected_frontend_function_uses_auth_headers(
    func_name: str,
    file_name: str,
    http_method: str,
    route_pattern: str,
    contract_ref: str,
    allow_content_type: bool,
):
    """
    Asserts each exported protected function:
    1. Explicitly calls getAuthHeaders()
    2. Passes headers into fetchWithTimeout
    3. Never manually sets Content-Type for multipart upload (let browser set boundary)
    4. Propagates 401/403 ApiError and never falls back to fake success
    """
    file_path = FRONTEND_SERVICES_DIR / file_name
    assert file_path.exists(), f"Service file not found: {file_path}"
    
    content = file_path.read_text(encoding="utf-8")
    func_body = extract_function_body(content, func_name)
    
    # 1. Must invoke getAuthHeaders
    assert "getAuthHeaders" in func_body, (
        f"[{contract_ref}] Function '{func_name}' in '{file_name}' must explicitly call getAuthHeaders()."
    )
    
    # 2. Must pass headers in fetchWithTimeout options
    assert re.search(r"fetchWithTimeout\s*\(\s*[^,]+,\s*\{[^}]*headers", func_body, re.DOTALL), (
        f"[{contract_ref}] Function '{func_name}' in '{file_name}' must pass headers in fetchWithTimeout options."
    )
    
    # 3. For multipart upload (uploadDocument), Content-Type must NOT be manually set
    if not allow_content_type and func_name == "uploadDocument":
        assert not re.search(r"['\"]Content-Type['\"]\s*:", func_body), (
            f"[{contract_ref}] Function '{func_name}' MUST NOT set Content-Type manually for FormData/multipart."
        )
    
    # 4. Must not swallow 401/403 into fake offline fallback
    assert not re.search(r"catch\s*\([^)]*\)\s*\{[^}]*return\s+(mockDoc|newWs|matched|localFallbackWorkspaces)", func_body), (
        f"[{contract_ref}] Function '{func_name}' must throw on 401/403 and never return fake success data."
    )
