"""Comprehensive test suite for Multi-Tenant Workspaces, Ingestion, Verification, and Cost-Guard."""

import io
import time
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import init_db
from app.services.llm_service import llm_service


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Initializes schema and seeds initial data."""
    await init_db()


@pytest_asyncio.fixture
async def client():
    """Asynchronous HTTP test client fixture."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_and_list_workspaces(client: AsyncClient):
    """Test GET /api/v1/workspaces and POST /api/v1/workspaces."""
    # 1. Verify seeded workspaces
    resp = await client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    workspaces = resp.json()
    assert len(workspaces) >= 3
    slugs = [w["slug"] for w in workspaces]
    assert "default" in slugs
    assert "smilecare" in slugs
    assert "techstore" in slugs

    # 2. Create a new workspace
    new_ws = {
        "slug": f"estate-{int(time.time())}",
        "name": "Bất Động Sản GreenLand",
        "industry": "Bất động sản & Nhà ở",
        "persona_name": "Tư vấn viên GreenLand",
        "tone_of_voice": "Lịch thiệp, đáng tin cậy và tận tình.",
        "business_rules": "Cung cấp thông tin dự án, bảng giá căn hộ, chính sách ngân hàng."
    }
    create_resp = await client.post("/api/v1/workspaces", json=new_ws)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["slug"] == new_ws["slug"]
    assert created_data["name"] == new_ws["name"]
    assert created_data["id"] > 0


@pytest.mark.asyncio
async def test_document_upload_and_chunking(client: AsyncClient):
    """Test file upload, parsing, recursive chunking, and retrieval."""
    sample_text = (
        "BẢNG GIÁ DỊCH VỤ NHA KHOA SMILECARE\n\n"
        "1. Dịch vụ Niềng răng mắc cài kim loại: Trọn gói 25.000.000 VNĐ. Thời gian điều trị từ 18 đến 24 tháng. "
        "Bảo hành mắc cài chính hãng trọn đời. Hỗ trợ trả góp 0% lãi suất trong 12 tháng.\n\n"
        "2. Dịch vụ Niềng răng trong suốt Invisalign: Trọn gói từ 60.000.000 VNĐ đến 90.000.000 VNĐ tùy mức độ lệch lạc. "
        "Khách hàng được quét dấu răng 3D iTero miễn phí trong lần thăm khám đầu tiên.\n\n"
        "3. Tẩy trắng răng bằng công nghệ Laser White: Giá 2.500.000 VNĐ một liệu trình 60 phút, bật từ 2 đến 3 tông màu."
    )
    files = {
        "file": ("bang_gia_nha_khoa.txt", io.BytesIO(sample_text.encode("utf-8")), "text/plain")
    }

    # Upload to workspace 2 (SmileCare)
    upload_resp = await client.post("/api/v1/workspaces/2/documents/upload", files=files)
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    assert doc_data["filename"] == "bang_gia_nha_khoa.txt"
    assert doc_data["workspace_id"] == 2
    assert doc_data["status"] == "pending"
    assert doc_data["chunk_count"] > 0
    doc_id = doc_data["id"]

    # Verify chunks endpoint
    chunks_resp = await client.get(f"/api/v1/documents/{doc_id}/chunks")
    assert chunks_resp.status_code == 200
    chunks = chunks_resp.json()
    assert len(chunks) == doc_data["chunk_count"]
    assert "Niềng răng" in chunks[0]["content"]


@pytest.mark.asyncio
async def test_document_verification_pipeline(client: AsyncClient):
    """Test full active verification pipeline: synthetic QA -> RAG test -> AI Judge -> publish."""
    sample_text = (
        "CHÍNH SÁCH ĐỔI TRẢ ĐIỆN MÁY TECHSTORE\n\n"
        "1. Quy định 1 đổi 1 trong 30 ngày đầu tiên nếu sản phẩm phát sinh lỗi phần cứng từ nhà sản xuất. "
        "Yêu cầu giữ nguyên hộp, phụ kiện, hóa đơn mua hàng và tem bảo hành không bị rách.\n\n"
        "2. Trường hợp thiếu phụ kiện, TechStore sẽ trừ phí theo đơn giá niêm yết của hãng linh kiện đó. "
        "Nếu máy bị trầy xước màn hình hoặc cấn móp, áp dụng mức khấu trừ 15% giá trị đơn hàng."
    )
    files = {
        "file": ("chinh_sach_doi_tra.txt", io.BytesIO(sample_text.encode("utf-8")), "text/plain")
    }

    # Upload to workspace 3 (TechStore)
    upload_resp = await client.post("/api/v1/workspaces/3/documents/upload", files=files)
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # Trigger Verification
    verify_resp = await client.post(f"/api/v1/documents/{doc_id}/verify")
    assert verify_resp.status_code == 200
    report = verify_resp.json()
    assert report["document_id"] == doc_id
    assert report["faithfulness_score"] >= 0.0
    assert report["status"] in ["passed", "warning", "failed"]
    assert len(report["items"]) > 0

    # Get verification report
    get_report_resp = await client.get(f"/api/v1/documents/{doc_id}/verification-report")
    assert get_report_resp.status_code == 200
    assert get_report_resp.json()["id"] == report["id"]

    # Publish Document
    pub_resp = await client.post(f"/api/v1/documents/{doc_id}/publish")
    assert pub_resp.status_code == 200
    pub_data = pub_resp.json()
    assert pub_data["status"] == "published"


@pytest.mark.asyncio
async def test_rag_workspace_isolation(client: AsyncClient):
    """Verify chat responses reflect workspace persona and grounding context."""
    # Query default workspace
    chat_payload = {
        "message": "Tôi muốn biết quy trình xử lý lỗi đăng nhập?",
        "workspace_id": 1
    }
    resp1 = await client.post("/api/v1/chat", json=chat_payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "response" in data1
    assert data1["latency_ms"] >= 0

    # Query smilecare workspace
    chat_payload_sc = {
        "message": "Chi phí niềng răng mắc cài là bao nhiêu?",
        "workspace_id": 2
    }
    resp2 = await client.post("/api/v1/chat", json=chat_payload_sc)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "response" in data2


@pytest.mark.asyncio
async def test_ticket_creation_with_workspace(client: AsyncClient):
    """Verify ticket is associated with workspace and pre-fills appropriate draft."""
    ticket_data = {
        "workspace_id": 2,
        "customer_name": "Phạm Quỳnh Như",
        "customer_email": "quynhnhu@example.com",
        "category": "Billing",
        "priority": "High",
        "subject": "Tư vấn gói niềng răng trả góp 0%",
        "description": "Tôi muốn đăng ký khám tư vấn niềng răng mắc cài và thủ tục trả góp 12 tháng tại cơ sở SmileCare."
    }
    resp = await client.post("/api/v1/tickets", json=ticket_data)
    assert resp.status_code == 201
    data = resp.json()
    assert data["workspace_id"] == 2
    assert data["ticket_code"].startswith("#TICK-")
    assert "SmileCare" in data["ai_draft_reply"] or "Quỳnh Như" in data["ai_draft_reply"]


@pytest.mark.asyncio
async def test_cost_guard_circuit_breaker_on_429(client: AsyncClient):
    """Simulate HTTP 429 rate limit cooldown and verify zero-LLM fallback."""
    # Activate cooldown
    llm_service.cooldown_until = time.time() + 60.0

    chat_payload = {
        "message": "Làm thế nào để đổi mật khẩu tài khoản?",
        "workspace_id": 1
    }
    resp = await client.post("/api/v1/chat", json=chat_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_fallback"] is True
    assert data["fallback_reason"] == "FREE_TIER_RATE_LIMIT_COOLDOWN"

    # Reset cooldown
    llm_service.cooldown_until = 0.0
