"""Base type definitions for category templates."""
from dataclasses import dataclass, field
from typing import Dict, List

FORBIDDEN_EXPRESSIONS: List[str] = [
    "혁신적",
    "획기적",
    "압도적",
    "게임체인저",
    "게임 체인저",
    "시장 재편",
    "완전히 바꾼다",
    "완전히 바꿀",
]

ALLOWED_IMPLICATION_PATTERNS: List[str] = [
    "~로 볼 수 있다",
    "~가능성이 있다",
    "~에 기여할 수 있다",
]


@dataclass
class CategoryTemplate:
    category: str
    sections: List[str]
    # maps section index (s1, s2...) to relevant JSON field paths
    evidence_map: Dict[str, List[str]] = field(default_factory=dict)
