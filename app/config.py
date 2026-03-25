import json
import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent

load_dotenv(BASE_DIR / ".env")

def load_field_rules() -> dict:
    rules_path = BASE_DIR / "field_rules.json"
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)

FIELD_RULES = load_field_rules()

SUPPORTED_CATEGORIES = list(FIELD_RULES["categories"].keys())

GLOBAL_RULES = FIELD_RULES["global_rules"]


def _strip_separators(s: str) -> str:
    """Remove spaces and common separator characters for loose matching."""
    return re.sub(r'[\s·/·\-_·,·.]+', '', s).lower()


# Pre-build a lookup: normalized key → canonical category name
_CATEGORY_NORMALIZED: dict[str, str] = {
    _strip_separators(cat): cat for cat in SUPPORTED_CATEGORIES
}


def normalize_category(value: str) -> Optional[str]:
    """Return the canonical category name for a possibly-variant input.

    Handles differences in spacing, separators (·, /, space, _), and case.
    Returns None if no match is found.

    Examples:
        "상품/서비스"  → "상품·서비스"
        "상품 서비스" → "상품·서비스"
        "해외동향"    → "해외 동향"
        "해외_동향"   → "해외 동향"
        "푸드 테크"   → "푸드테크"
    """
    if value in SUPPORTED_CATEGORIES:
        return value
    key = _strip_separators(value)
    return _CATEGORY_NORMALIZED.get(key)
