from typing import List, Optional, Any
from pydantic import BaseModel, field_validator
import re


SOURCE_ID_PATTERN = re.compile(r"^S[1-9][0-9]*$")


class SourceMaster(BaseModel):
    source_id: str
    url: str
    title: str
    publisher: str
    published_at: Optional[str] = None
    source_type: str = "article"
    language: Optional[str] = None
    relevance_score: Optional[float] = None
    is_duplicate: bool = False

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, v: str) -> str:
        if not SOURCE_ID_PATTERN.match(v):
            raise ValueError(f"source_id must match pattern S[1-9][0-9]*, got: {v}")
        return v

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        allowed = {"article", "official_site", "press_release", "product_page", "report", "blog", "video", "other"}
        if v not in allowed:
            raise ValueError(f"source_type must be one of {allowed}")
        return v


class ValueWithSources(BaseModel):
    value: str = ""
    sources: List[str] = []
    notes: str = ""

    def is_empty(self) -> bool:
        return not self.value or self.value.strip() == ""

    def has_sources(self) -> bool:
        return len(self.sources) > 0

    def validate_source_refs(self, valid_ids: set) -> List[str]:
        """Return list of invalid source_id references."""
        return [sid for sid in self.sources if sid not in valid_ids]
