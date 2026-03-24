"""Template for 해외 동향 category."""
from app.blog.templates.base import CategoryTemplate

TREND_TEMPLATE = CategoryTemplate(
    category="해외 동향",
    sections=[
        "트렌드 개요",
        "발생 배경",
        "구조적 변화",
        "주요 사례",
        "확산 가능성 / 시사점",
    ],
    evidence_map={
        "s1": ["trend_name", "definition", "change_from_previous"],
        "s2": ["background"],
        "s3": ["core_change_structure.product_change", "core_change_structure.consumption_change"],
        "s4": ["cases"],
        "s5": ["expansion_pattern.geographic_scope", "expansion_pattern.industry_expansion"],
    },
)
