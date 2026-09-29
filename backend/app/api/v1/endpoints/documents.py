"""Document ingestion, chunking inspection, verification, and publication endpoints."""

from typing import List
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.document import Document
from app.models.workspace import Workspace
from app.models.knowledge import KnowledgeChunk
from app.models.verification import VerificationReport, VerificationItem
from app.schemas.document import (
    DocumentResponse,
    DocumentChunkResponse,
    DocumentPublishResponse,
)
from app.schemas.verification import (
    VerificationReportResponse,
    VerificationItemResponse,
)
from app.services.document_service import document_service
from app.services.verification_service import verification_service

logger = logging.getLogger("smartdesk.api.documents")
router = APIRouter()


# ---------------------------------------------------------
# Workspace-scoped Document Management
# ---------------------------------------------------------

@router.post(
    "/workspaces/{workspace_id}/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload knowledge file to workspace"
)
async def upload_document(
    workspace_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> DocumentResponse:
    """Upload PDF, TXT, or MD knowledge file for ingestion and recursive chunking."""
    ws = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    if not ws.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Workspace với ID {workspace_id}."
        )

    try:
        content_bytes = await file.read()
        filename = file.filename or "uploaded_document.txt"
        doc = await document_service.process_and_store_document(
            file_bytes=content_bytes,
            filename=filename,
            workspace_id=workspace_id,
            session=db
        )
        return DocumentResponse.model_validate(doc)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing document upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi xử lý tệp: {str(e)}"
        )


@router.get(
    "/workspaces/{workspace_id}/documents",
    response_model=List[DocumentResponse],
    summary="List workspace documents"
)
async def list_workspace_documents(
    workspace_id: int,
    db: AsyncSession = Depends(get_db)
) -> List[DocumentResponse]:
    """Retrieve all uploaded documents for a specific workspace."""
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .order_by(Document.id.desc())
    )
    docs = result.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


# ---------------------------------------------------------
# Document-specific Operations
# ---------------------------------------------------------

@router.get(
    "/documents/{document_id}/chunks",
    response_model=List[DocumentChunkResponse],
    summary="Get document chunks"
)
async def get_document_chunks(
    document_id: int,
    db: AsyncSession = Depends(get_db)
) -> List[DocumentChunkResponse]:
    """Retrieve fine-grained vector chunks of a specific document."""
    result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == document_id)
        .order_by(KnowledgeChunk.chunk_index)
    )
    chunks = result.scalars().all()
    return [DocumentChunkResponse.model_validate(c) for c in chunks]


@router.delete(
    "/documents/{document_id}",
    summary="Delete document safely"
)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Safely delete document and cascade chunks/verification reports."""
    deleted = await document_service.delete_document_safely(document_id, db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tài liệu ID {document_id}."
        )
    return {"ok": True, "message": f"Đã xóa thành công tài liệu ID {document_id}."}


# ---------------------------------------------------------
# Active Verification & Publication Gate
# ---------------------------------------------------------

@router.post(
    "/documents/{document_id}/verify",
    response_model=VerificationReportResponse,
    summary="Execute active knowledge verification"
)
async def verify_document_endpoint(
    document_id: int,
    db: AsyncSession = Depends(get_db)
) -> VerificationReportResponse:
    """
    Triggers 3-step active verification:
    1. Synthetic QA generation
    2. Parallel RAG self-test
    3. AI Judge faithfulness scoring
    """
    try:
        report = await verification_service.verify_document(document_id, db)
        # Load items
        items_result = await db.execute(
            select(VerificationItem)
            .where(VerificationItem.report_id == report.id)
            .order_by(VerificationItem.id)
        )
        items = items_result.scalars().all()

        return VerificationReportResponse(
            id=report.id,
            document_id=report.document_id,
            workspace_id=report.workspace_id,
            faithfulness_score=report.faithfulness_score,
            status=report.status,
            created_at=report.created_at,
            items=[VerificationItemResponse.model_validate(it) for it in items]
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during verification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi trong quá trình thẩm định tri thức: {str(e)}"
        )


@router.get(
    "/documents/{document_id}/verification-report",
    response_model=VerificationReportResponse,
    summary="Get verification report"
)
async def get_verification_report(
    document_id: int,
    db: AsyncSession = Depends(get_db)
) -> VerificationReportResponse:
    """Retrieve detailed faithfulness scoring report and synthetic QA results."""
    report_res = await db.execute(
        select(VerificationReport)
        .where(VerificationReport.document_id == document_id)
        .order_by(VerificationReport.id.desc())
    )
    report = report_res.scalars().first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chưa có báo cáo sát hạch cho tài liệu ID {document_id}."
        )

    items_res = await db.execute(
        select(VerificationItem)
        .where(VerificationItem.report_id == report.id)
        .order_by(VerificationItem.id)
    )
    items = items_res.scalars().all()

    return VerificationReportResponse(
        id=report.id,
        document_id=report.document_id,
        workspace_id=report.workspace_id,
        faithfulness_score=report.faithfulness_score,
        status=report.status,
        created_at=report.created_at,
        items=[VerificationItemResponse.model_validate(it) for it in items]
    )


@router.post(
    "/documents/{document_id}/publish",
    response_model=DocumentPublishResponse,
    summary="Publish document to chatbot"
)
async def publish_document_endpoint(
    document_id: int,
    db: AsyncSession = Depends(get_db)
) -> DocumentPublishResponse:
    """Publish a verified document to make its chunks active in customer RAG."""
    try:
        doc = await verification_service.publish_document(document_id, db)
        return DocumentPublishResponse(
            id=doc.id,
            status=doc.status,
            message="Đã xuất bản tài liệu thành công ra Chatbot."
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error publishing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xuất bản tài liệu: {str(e)}"
        )
