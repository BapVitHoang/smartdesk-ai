"""Security utilities: input sanitization and prompt injection defense."""

import re
from typing import Tuple

# Common prompt injection signatures and malicious jailbreak patterns
PROMPT_INJECTION_PATTERNS = [
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
    r"output\s+the\s+system\s+prompt"
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
