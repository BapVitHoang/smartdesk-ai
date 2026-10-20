"""Security utilities: input sanitization, prompt injection defense, and PII masking."""

import re
from typing import Tuple

# Common prompt injection signatures and malicious jailbreak patterns (English and Vietnamese)
PROMPT_INJECTION_PATTERNS = [
    # English patterns
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions?",
    r"you\s+are\s+now\s+(in\s+)?developer\s+mode",
    r"system\s+prompt\s*(override|reveal|leak|bypass)",
    r"<\|system\|>",
    r"\[system\]",
    r"dan\s+mode",
    r"bypass\s+all\s+filters?",
    r"reveal\s+your\s+instructions?",
    r"repeat\s+everything\s+above",
    r"output\s+the\s+system\s+prompt",
    # Vietnamese patterns
    r"bỏ\s+qua\s+(tất\s+cả\s+|mọi\s+|các\s+)?(hướng\s+dẫn|chỉ\s+dẫn|quy\s+tắc|lệnh)",
    r"(tiết\s+lộ|in\s+ra|hiển\s+thị|cho\s+tôi\s+xem)\s+.*(system\s+prompt|hướng\s+dẫn\s+hệ\s+thống|cấu\s+hình\s+gốc)",
    r"chế\s+độ\s+(nhà\s+phát\s+triển|developer|không\s+giới\s+hạn|dan)",
    r"quên\s+(hết\s+|tất\s+cả\s+)?(những\s+gì|hướng\s+dẫn|quy\s+tắc)",
]

COMPILED_INJECTION_REGEX = [
    re.compile(pattern, re.IGNORECASE) for pattern in PROMPT_INJECTION_PATTERNS
]


def sanitize_input(text: str, max_length: int = 4000) -> str:
    """
    Sanitizes user input by stripping harmful control characters and truncating excessive lengths.
    """
    if not text:
        return ""

    # Strip null bytes and non-printable control characters (except newline, tab, carriage return)
    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\r\t")

    # Truncate if exceeds max length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned.strip()


def check_prompt_injection(text: str) -> Tuple[bool, str]:
    """
    Scans the provided text against known prompt injection and jailbreak signatures.

    Returns:
        Tuple[bool, str]: (is_suspicious, matched_pattern_or_reason)
    """
    if not text:
        return False, ""

    for regex in COMPILED_INJECTION_REGEX:
        match = regex.search(text)
        if match:
            return True, f"Suspicious prompt token detected: '{match.group(0)}'"

    return False, ""


def redact_pii(text: str) -> str:
    """
    Masks sensitive personal identifiable information (PII) before external LLM calls.
    Masks emails, phone numbers, and CCCD/card numbers while preserving monetary prices and ticket codes.
    """
    if not text:
        return ""

    # 1. Mask Email addresses
    redacted = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[REDACTED_EMAIL]",
        text
    )

    # 2. Mask 10-digit Vietnamese phone numbers (+84... or 03/05/07/08/09...)
    redacted = re.sub(
        r"(?:\+84|0)[35789]\d{8}\b",
        "[REDACTED_PHONE]",
        redacted
    )

    # 3. Mask 16-digit credit cards or 12-digit Vietnamese CCCD (while NOT touching prices like 25.000.000 VNĐ)
    redacted = re.sub(
        r"\b\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{4}\b",
        "[REDACTED_ID]",
        redacted
    )
    redacted = re.sub(
        r"(?<![\d.,])\b\d{12}\b(?![\d.,])",
        "[REDACTED_ID]",
        redacted
    )

    return redacted
