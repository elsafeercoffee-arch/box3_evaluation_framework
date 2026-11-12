import os
import re
from fastapi import Header, HTTPException, status

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"تجاهل\s+(جميع\s+)?التعليمات",
    r"تجاهل\s+النصوص\s+القانونية",
    r"اطبع\s+.*البرومبت",
    r"وضع\s+المطور",
    r"كود\s+بايثون\s+لحذف",
    r"تم\s+الاختراق",
    r"أمر\s+نظامي\s+عاجل",
]
INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(?:\+?20|0020|\+?966|\+?971)?0?1[0125]\d{8}|\b05\d{8}\b")
NID_RE = re.compile(r"\b[23]\d{13}\b")


def verify_api_key(x_api_key: str = Header(default="")) -> str:
    expected = os.getenv("API_KEY", "dev-box3-secret-key")
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )
    return x_api_key


def mask_pii(text: str) -> str:
    masked = EMAIL_RE.sub("[EMAIL]", text)
    masked = NID_RE.sub("[NATIONAL_ID]", masked)
    masked = PHONE_RE.sub("[PHONE]", masked)
    return masked


def is_prompt_injection(text: str) -> bool:
    return bool(INJECTION_RE.search(text or ""))
