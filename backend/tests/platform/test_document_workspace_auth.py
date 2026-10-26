"""RBAC tests: document ingestion and workspace mutation endpoints require an admin JWT."""

import io
from typing import Any, Dict, Optional

import pytest
from httpx import AsyncClient

PROTECTED_CALLS = [
    ("post", "/api/v1/workspaces/2/documents/upload", None),
    ("get", "/api/v1/workspaces/2/documents", None),
    ("get", "/api/v1/documents/1/chunks", None),
    ("delete", "/api/v1/documents/999999", None),
    ("post", "/api/v1/documents/1/verify", None),
    ("get", "/api/v1/documents/1/verification-report", None),
    ("post", "/api/v1/documents/1/publish", None),
    (
        "post",
        "/api/v1/workspaces",
        {"slug": "rbac-test", "name": "RBAC", "industry": "Test"},
    ),
    ("put", "/api/v1/workspaces/2", {"persona_name": "Hacked"}),
]


async def _call(
    client: AsyncClient, method: str, url: str, body: Optional[Dict[str, Any]]
):
    if url.endswith("/upload"):
        files = {"file": ("a.txt", io.BytesIO(b"noi dung kiem thu"), "text/plain")}
        return await client.post(url, files=files)
    if body is not None:
        return await getattr(client, method)(url, json=body)
    return await getattr(client, method)(url)


@pytest.mark.asyncio
@pytest.mark.parametrize("method,url,body", PROTECTED_CALLS)
async def test_protected_endpoints_reject_anonymous(
    unauth_client: AsyncClient, method: str, url: str, body
):
    res = await _call(unauth_client, method, url, body)
    assert res.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("method,url,body", PROTECTED_CALLS)
async def test_protected_endpoints_reject_customer_role(
    user_client: AsyncClient, method: str, url: str, body
):
    res = await _call(user_client, method, url, body)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_workspace_listing_stays_public(unauth_client: AsyncClient):
    res = await unauth_client.get("/api/v1/workspaces")
    assert res.status_code == 200
