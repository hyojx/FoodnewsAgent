from typing import List, Optional
from pydantic import BaseModel
from app.models.common import ValueWithSources, SourceMaster


# ─── 해외 동향 ───────────────────────────────────────────────────────────────

class CaseItem(BaseModel):
    company: ValueWithSources = ValueWithSources()
    product_or_service: ValueWithSources = ValueWithSources()
    how_it_works: ValueWithSources = ValueWithSources()
    features: List[ValueWithSources] = []


class CoreChangeStructure(BaseModel):
    product_change: ValueWithSources = ValueWithSources()
    consumption_change: ValueWithSources = ValueWithSources()


class ExpansionPattern(BaseModel):
    geographic_scope: ValueWithSources = ValueWithSources()
    industry_expansion: ValueWithSources = ValueWithSources()


class OverseasTrendSchema(BaseModel):
    category: str = "해외 동향"
    topic: str = ""
    researched_at: str = ""
    sources_master: List[SourceMaster] = []
    trend_name: ValueWithSources = ValueWithSources()
    definition: ValueWithSources = ValueWithSources()
    change_from_previous: ValueWithSources = ValueWithSources()
    background: List[ValueWithSources] = []
    core_change_structure: CoreChangeStructure = CoreChangeStructure()
    cases: List[CaseItem] = []
    expansion_pattern: ExpansionPattern = ExpansionPattern()


# ─── 상품·서비스 ──────────────────────────────────────────────────────────────

class DeveloperInfo(BaseModel):
    company_name: ValueWithSources = ValueWithSources()
    company_description: ValueWithSources = ValueWithSources()


class BusinessModel(BaseModel):
    pricing: ValueWithSources = ValueWithSources()
    model: ValueWithSources = ValueWithSources()


class ProductServiceSchema(BaseModel):
    category: str = "상품·서비스"
    topic: str = ""
    researched_at: str = ""
    sources_master: List[SourceMaster] = []
    name: ValueWithSources = ValueWithSources()
    summary: ValueWithSources = ValueWithSources()
    developer: DeveloperInfo = DeveloperInfo()
    purpose: ValueWithSources = ValueWithSources()
    key_features: List[ValueWithSources] = []
    how_it_works: ValueWithSources = ValueWithSources()
    data_or_technology_basis: List[ValueWithSources] = []
    business_model: BusinessModel = BusinessModel()
    use_effects: List[ValueWithSources] = []
    differentiation: ValueWithSources = ValueWithSources()


# ─── 푸드테크 ──────────────────────────────────────────────────────────────────

class ApplicationItem(BaseModel):
    company: ValueWithSources = ValueWithSources()
    application_form: ValueWithSources = ValueWithSources()


class FoodtechSchema(BaseModel):
    category: str = "푸드테크"
    topic: str = ""
    researched_at: str = ""
    sources_master: List[SourceMaster] = []
    technology_name: ValueWithSources = ValueWithSources()
    summary: ValueWithSources = ValueWithSources()
    technology_principle: ValueWithSources = ValueWithSources()
    problem_with_existing_method: ValueWithSources = ValueWithSources()
    solution: ValueWithSources = ValueWithSources()
    applications: List[ApplicationItem] = []
    results_and_effects: List[ValueWithSources] = []
    use_cases: List[ValueWithSources] = []
    industry_meaning: ValueWithSources = ValueWithSources()


# ─── Union helper ─────────────────────────────────────────────────────────────

CATEGORY_SCHEMA_MAP = {
    "해외 동향": OverseasTrendSchema,
    "상품·서비스": ProductServiceSchema,
    "푸드테크": FoodtechSchema,
}


def get_empty_schema(category: str) -> dict:
    schema_cls = CATEGORY_SCHEMA_MAP.get(category)
    if schema_cls is None:
        raise ValueError(f"Unsupported category: {category}")
    return schema_cls().model_dump()
