"""Outline JSON schema — strict 4-6 section validation."""
from typing import Dict, List
from pydantic import BaseModel, field_validator


class OutlineSection(BaseModel):
    heading: str
    points: List[str]


class OutlineJSON(BaseModel):
    title: str
    lead_angle: str
    sections: List[OutlineSection]
    evidence_map: Dict[str, List[str]] = {}

    @field_validator("sections")
    @classmethod
    def validate_section_count(cls, v: List[OutlineSection]) -> List[OutlineSection]:
        if not (4 <= len(v) <= 6):
            raise ValueError(f"Outline must have 4-6 sections, got {len(v)}")
        return v
