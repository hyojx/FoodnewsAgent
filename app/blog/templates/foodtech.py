"""Template for 푸드테크 category."""
from app.blog.templates.base import CategoryTemplate

FOODTECH_TEMPLATE = CategoryTemplate(
    category="푸드테크",
    sections=[
        "기술 개요",
        "기존 한계와 해결 방식",
        "적용 방식",
        "상용화 단계",
        "시사점",
    ],
    evidence_map={
        "s1": ["technology_name", "summary", "technology_principle"],
        "s2": ["problem_with_existing_method", "solution"],
        "s3": ["applications"],
        "s4": ["results_and_effects", "use_cases"],
        "s5": ["industry_meaning"],
    },
)
