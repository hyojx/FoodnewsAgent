"""Input article JSON validation schema."""
from typing import Any, Dict
from pydantic import BaseModel, field_validator

SUPPORTED_CATEGORIES = ["상품·서비스", "푸드테크", "해외 동향"]


class ArticleInput(BaseModel):
    article_json: Dict[str, Any]

    @field_validator("article_json")
    @classmethod
    def validate_article_json(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not v:
            raise ValueError("article_json must not be empty")
        category = v.get("category", "")
        if category not in SUPPORTED_CATEGORIES:
            raise ValueError(
                f"article_json.category must be one of {SUPPORTED_CATEGORIES}, got '{category}'"
            )
        return v
