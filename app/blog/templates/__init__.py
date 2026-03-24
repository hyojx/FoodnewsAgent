from app.blog.templates.base import CategoryTemplate, FORBIDDEN_EXPRESSIONS
from app.blog.templates.product import PRODUCT_TEMPLATE
from app.blog.templates.foodtech import FOODTECH_TEMPLATE
from app.blog.templates.trend import TREND_TEMPLATE

CATEGORY_TEMPLATES: dict[str, CategoryTemplate] = {
    "상품·서비스": PRODUCT_TEMPLATE,
    "푸드테크": FOODTECH_TEMPLATE,
    "해외 동향": TREND_TEMPLATE,
}


def get_template(category: str) -> CategoryTemplate:
    template = CATEGORY_TEMPLATES.get(category)
    if template is None:
        raise ValueError(f"Unknown category: '{category}'")
    return template


__all__ = [
    "CategoryTemplate",
    "FORBIDDEN_EXPRESSIONS",
    "PRODUCT_TEMPLATE",
    "FOODTECH_TEMPLATE",
    "TREND_TEMPLATE",
    "CATEGORY_TEMPLATES",
    "get_template",
]
