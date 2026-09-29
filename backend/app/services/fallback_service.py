"""Pure Python deterministic BM25 / Keyword FAQ Matcher for zero-LLM fallback."""

import json
import math
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import logging

from app.core.config import settings

logger = logging.getLogger("smartdesk.fallback")

# Standard English and basic Vietnamese stopwords
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "did", "do", "does", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is",
    "isn't", "it", "its", "itself", "let's", "me", "more", "most", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should",
    "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "we", "were", "what",
    "when", "where", "which", "while", "who", "whom", "why", "with", "would",
    "you", "your", "yours", "yourself", "yourselves",
    # Vietnamese common stopwords
    "la", "la", "cac", "nhung", "va", "cua", "trong", "co", "duoc", "de", "cho",
    "voi", "khong", "toi", "ban", "ve", "nay", "do", "khi", "nhu", "tai"
}


def tokenize(text: str) -> List[str]:
    """Tokenize string into lowercase alphanumeric terms with stopwords removed."""
    if not text:
        return []
    words = re.findall(r"\w+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


class BM25Engine:
    """Lightweight in-memory BM25 ranker for curated documents."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents: List[Dict[str, Any]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.total_docs: int = 0

    def fit(self, docs: List[Dict[str, Any]]) -> None:
        """Indexes documents and computes corpus statistics."""
        self.documents = docs
        self.total_docs = len(docs)
        if self.total_docs == 0:
            return

        self.doc_lengths = []
        self.doc_freqs = {}

        for doc in docs:
            # Weighted tokens: Give double weight to title tokens
            title_tokens = tokenize(doc.get("title", ""))
            content_tokens = tokenize(doc.get("content", ""))
            all_tokens = title_tokens + title_tokens + content_tokens
            
            self.doc_lengths.append(len(all_tokens))
            unique_tokens = set(all_tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.avg_doc_len = sum(self.doc_lengths) / max(self.total_docs, 1)

    def score(self, query: str) -> List[Tuple[Dict[str, Any], float]]:
        """Calculates BM25 relevance score for each document against the query."""
        if self.total_docs == 0:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores: List[Tuple[Dict[str, Any], float]] = []

        for idx, doc in enumerate(self.documents):
            title_tokens = tokenize(doc.get("title", ""))
            content_tokens = tokenize(doc.get("content", ""))
            doc_tokens = title_tokens + title_tokens + content_tokens
            doc_len = self.doc_lengths[idx]

            # Calculate term frequencies
            tf: Dict[str, int] = {}
            for t in doc_tokens:
                tf[t] = tf.get(t, 0) + 1

            doc_score = 0.0
            for q in query_tokens:
                if q not in tf:
                    continue

                freq = tf[q]
                df = self.doc_freqs.get(q, 0)
                # BM25 IDF formula
                idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
                # Term score
                numerator = freq * (self.k1 + 1.0)
                denominator = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / max(self.avg_doc_len, 1.0)))
                doc_score += idf * (numerator / denominator)

            if doc_score > 0:
                scores.append((doc, doc_score))

        # Sort descending by score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


class FallbackService:
    """Deterministic, zero-LLM FAQ Matcher and Escalation Provider."""

    def __init__(self, faq_file_path: Optional[str] = None) -> None:
        self.faq_file_path = Path(faq_file_path) if faq_file_path else settings.resolved_seed_faq_path
        self.bm25 = BM25Engine()
        self.faq_items: List[Dict[str, Any]] = []
        self._load_faq()

    def _load_faq(self) -> None:
        """Loads seed FAQs from local JSON file."""
        try:
            if self.faq_file_path.exists():
                with open(self.faq_file_path, "r", encoding="utf-8") as f:
                    self.faq_items = json.load(f)
                self.bm25.fit(self.faq_items)
                logger.info(f"FallbackService loaded {len(self.faq_items)} FAQs successfully.")
            else:
                logger.warning(f"Seed FAQ file not found at: {self.faq_file_path}")
                self.faq_items = []
        except Exception as e:
            logger.error(f"Failed to load seed FAQ file: {e}", exc_info=True)
            self.faq_items = []

    def match_faq(
        self,
        query: str,
        workspace_id: Optional[int] = 1,
        workspace_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Matches customer query deterministically against verified knowledge base.
        Ensures tenant isolation so non-default workspaces don't leak default IT FAQs.
        """
        ws_id = workspace_id or 1
        ws_label = workspace_name or (
            "Nha Khoa SmileCare" if ws_id == 2 else (
                "Điện Máy TechStore" if ws_id == 3 else "SmartDesk Cloud"
            )
        )

        # 1. Non-default workspaces do NOT leak default IT SaaS FAQs
        if ws_id != 1:
            return {
                "response": (
                    f"Hiện tại hệ thống trợ lý AI đang tạm thời gián đoạn kết nối thời gian thực. "
                    f"Chúng tôi chưa tìm thấy tài liệu phù hợp trong kho tri thức của {ws_label}.\n\n"
                    f"Để được hỗ trợ nhanh nhất và chính xác nhất, quý khách vui lòng bấm nút "
                    f"'Leo thang sự cố (Gửi Ticket ưu tiên)' để chuyển yêu cầu trực tiếp tới đội ngũ chuyên trách."
                ),
                "citations": [
                    {
                        "doc_id": f"ws-{ws_id}-support",
                        "title": f"Trung tâm hỗ trợ {ws_label}",
                        "source_url": "/tickets"
                    }
                ],
                "confidence": 0.40,
                "is_fallback": True,
                "escalation_recommended": True
            }

        # 2. For default IT workspace, query seed FAQs
        if not self.faq_items and self.faq_file_path.exists():
            self._load_faq()

        ranked = self.bm25.score(query)

        if ranked and ranked[0][1] > 0.8:
            top_doc, raw_score = ranked[0]
            confidence = min(0.85, max(0.40, round(raw_score / 15.0, 2)))
            
            response_text = (
                f"Hệ thống trợ lý AI thời gian thực đang bận hoặc gián đoạn kết nối. "
                f"Dựa trên Cơ sở tri thức đã xác thực, dưới đây là tài liệu liên quan nhất: '{top_doc['title']}':\n\n"
                f"{top_doc['content']}\n\n"
                f"Nếu thông tin trên chưa giải quyết trọn vẹn vấn đề, quý khách vui lòng bấm "
                f"'Leo thang sự cố (Gửi Ticket ưu tiên)' phía dưới để chuyên viên kỹ thuật hỗ trợ trực tiếp."
            )
            citations = [
                {
                    "doc_id": top_doc.get("doc_id", "faq-ref"),
                    "title": top_doc.get("title", "Knowledge Article"),
                    "source_url": top_doc.get("source_url", "/faq")
                }
            ]
            return {
                "response": response_text,
                "citations": citations,
                "confidence": confidence,
                "is_fallback": True,
                "escalation_recommended": confidence < 0.60
            }

        # No direct keyword/BM25 match found
        fallback_text = (
            "Hệ thống hiện đang gặp lượng truy cập lớn hoặc gián đoạn kết nối với bộ máy suy luận AI. "
            "Hiện tại chưa tìm thấy bài viết phù hợp chính xác với câu hỏi của quý khách trong cơ sở tri thức.\n\n"
            "Để nhận được hỗ trợ trực tiếp và kịp thời, quý khách vui lòng chuyển sang tab 'Gửi Ticket' "
            "để đội ngũ chuyên viên tiếp nhận xử lý."
        )
        return {
            "response": fallback_text,
            "citations": [
                {
                    "doc_id": "faq-general",
                    "title": "SmartDesk Help Center & Ticket Escalation",
                    "source_url": "/tickets"
                }
            ],
            "confidence": 0.30,
            "is_fallback": True,
            "escalation_recommended": True
        }


fallback_service = FallbackService()
