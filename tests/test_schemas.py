"""Tests for category-specific schema validation and Pydantic model integrity."""
import pytest
from pydantic import ValidationError
from app.models.common import SourceMaster, ValueWithSources
from app.models.category_schemas import (
    OverseasTrendSchema,
    ProductServiceSchema,
    FoodtechSchema,
    get_empty_schema,
    CATEGORY_SCHEMA_MAP,
)


# ─── ValueWithSources ────────────────────────────────────────────────────────

def test_value_with_sources_defaults():
    vws = ValueWithSources()
    assert vws.value == ""
    assert vws.sources == []
    assert vws.notes == ""
    assert vws.is_empty() is True
    assert vws.has_sources() is False


def test_value_with_sources_filled():
    vws = ValueWithSources(value="Test", sources=["S1", "S2"])
    assert vws.is_empty() is False
    assert vws.has_sources() is True


def test_value_with_sources_validate_refs():
    vws = ValueWithSources(value="Test", sources=["S1", "S3"])
    invalid = vws.validate_source_refs({"S1", "S2"})
    assert "S3" in invalid
    assert "S1" not in invalid


# ─── SourceMaster ────────────────────────────────────────────────────────────

def test_source_master_valid():
    s = SourceMaster(
        source_id="S1",
        url="https://example.com",
        title="Article",
        publisher="Media",
        source_type="article",
    )
    assert s.source_id == "S1"


def test_source_master_invalid_source_id():
    with pytest.raises(ValidationError):
        SourceMaster(
            source_id="INVALID",
            url="https://example.com",
            title="Article",
            publisher="Media",
        )


def test_source_master_invalid_source_type():
    with pytest.raises(ValidationError):
        SourceMaster(
            source_id="S1",
            url="https://example.com",
            title="Article",
            publisher="Media",
            source_type="unknown_type",
        )


# ─── OverseasTrendSchema ─────────────────────────────────────────────────────

def test_overseas_trend_defaults():
    schema = OverseasTrendSchema()
    assert schema.category == "해외 동향"
    assert schema.topic == ""
    assert schema.sources_master == []
    assert schema.cases == []


def test_overseas_trend_schema_round_trip():
    schema = OverseasTrendSchema()
    dumped = schema.model_dump()
    assert dumped["category"] == "해외 동향"
    assert "trend_name" in dumped
    assert "expansion_pattern" in dumped
    assert "core_change_structure" in dumped


# ─── ProductServiceSchema ────────────────────────────────────────────────────

def test_product_service_defaults():
    schema = ProductServiceSchema()
    assert schema.category == "상품·서비스"
    assert schema.key_features == []
    assert schema.use_effects == []


def test_product_service_round_trip():
    schema = ProductServiceSchema()
    dumped = schema.model_dump()
    assert "business_model" in dumped
    assert "developer" in dumped
    assert "key_features" in dumped


# ─── FoodtechSchema ──────────────────────────────────────────────────────────

def test_foodtech_defaults():
    schema = FoodtechSchema()
    assert schema.category == "푸드테크"
    assert schema.applications == []
    assert schema.use_cases == []


def test_foodtech_round_trip():
    schema = FoodtechSchema()
    dumped = schema.model_dump()
    assert "technology_name" in dumped
    assert "applications" in dumped
    assert "industry_meaning" in dumped


# ─── get_empty_schema ────────────────────────────────────────────────────────

def test_get_empty_schema_all_categories():
    for cat in ["해외 동향", "상품·서비스", "푸드테크"]:
        schema = get_empty_schema(cat)
        assert isinstance(schema, dict)
        assert schema["category"] == cat
        assert "sources_master" in schema
        assert "topic" in schema
        assert "researched_at" in schema


def test_get_empty_schema_invalid_category():
    with pytest.raises(ValueError):
        get_empty_schema("invalid")


# ─── Category map ────────────────────────────────────────────────────────────

def test_category_schema_map_coverage():
    assert set(CATEGORY_SCHEMA_MAP.keys()) == {"해외 동향", "상품·서비스", "푸드테크"}
