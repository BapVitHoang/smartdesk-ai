"""Knowledge base article endpoints for FAQ browsing and RAG inspection."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
import logging

from app.models.knowledge import FAQItem
from app.schemas.knowledge import KnowledgeItemResponse
from app.services.fallback_service import fallback_service
from app.db.session import get_db

logger = logging.getLogger("smartdesk.api.knowledge")

router = APIRouter()


@router.get(
    "",
    response_model=List[KnowledgeItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List Knowledge Base Articles",
    description="Retrieve all curated FAQ knowledge articles with optional filtering by category or keyword search."
)
async def list_knowledge(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search keyword in title or content"),
    db: AsyncSession = Depends(get_db)
) -> List[KnowledgeItemResponse]:
    """List knowledge articles with optional category and search filters."""
    query = select(FAQItem)

    if category:
        query = query.where(FAQItem.category.ilike(category))

    if search:
        pattern = f"%{search}%"
        query = query.where(or_(FAQItem.title.ilike(pattern), FAQItem.content.ilike(pattern)))

    result = await db.execute(query)
    items = result.scalars().all()

    if items:
        return [KnowledgeItemResponse.model_validate(item) for item in items]

    filtered = fallback_service.faq_items
    if category:
        filtered = [f for f in filtered if f.get("category", "").lower() == category.lower()]
    if search:
        s_low = search.lower()
        filtered = [
            f for f in filtered
            if s_low in f.get("title", "").lower() or s_low in f.get("content", "").lower()
        ]

    return [KnowledgeItemResponse(**item) for item in filtered]


@router.get(
    "/{doc_id}",
    response_model=KnowledgeItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Knowledge Article Detail",
    description="Fetch a single knowledge base article by its doc_id."
)
async def get_knowledge_item(
    doc_id: str = Path(..., description="Document identifier"),
    db: AsyncSession = Depends(get_db)
) -> KnowledgeItemResponse:
    """Retrieve a specific knowledge article."""
    result = await db.execute(select(FAQItem).where(FAQItem.doc_id == doc_id))
    item = result.scalars().first()

    if item:
        return KnowledgeItemResponse.model_validate(item)

    for f in fallback_service.faq_items:
        if f.get("doc_id") == doc_id:
            return KnowledgeItemResponse(**f)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Knowledge article with doc_id '{doc_id}' not found."
    )
