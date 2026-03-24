"""Template for 상품·서비스 category."""
from app.blog.templates.base import CategoryTemplate

PRODUCT_TEMPLATE = CategoryTemplate(
    category="상품·서비스",
    sections=[
        "서비스 개요",
        "개발 배경 / 해결 문제",
        "핵심 기능",
        "이용 방식 / 도입 방식",
        "시사점",
    ],
    evidence_map={
        "s1": ["name", "summary", "developer.company_name", "developer.company_description"],
        "s2": ["purpose"],
        "s3": ["key_features", "how_it_works", "data_or_technology_basis"],
        "s4": ["business_model.pricing", "business_model.model"],
        "s5": ["use_effects", "differentiation"],
    },
)
