"""Knowledge base and FAQ article Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeItemResponse(BaseModel):
    """Knowledge article / FAQ item response representation."""

    model_config = ConfigDict(from_attributes=True)

    doc_id: str = Field(..., description="Unique article identifier", examples=["doc-01"])
    category: str = Field(..., description="Article category", examples=["Authentication"])
    title: str = Field(..., description="Article title", examples=["How to Reset Your CloudDesk / SmartDesk Password"])
    content: str = Field(..., description="Full text content of the article")
    source_url: str = Field(..., description="Canonical source URL", examples=["/faq/auth/password-reset"])