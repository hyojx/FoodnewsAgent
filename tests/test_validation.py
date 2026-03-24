"""Tests for source reference validation and schema integrity."""
import pytest
from app.services.validator import validate_source_references


def _make_sources_master(ids):
    return [
        {
            "source_id": sid,
            "url": f"https://example.com/{sid}",
            "title": f"Article {sid}",
            "publisher": "Test",
            "published_at": "2026-03-24",
            "source_type": "article",
            "is_duplicate": False,
        }
        for sid in ids
    ]


def test_valid_source_references():
    schema = {
        "category": "해외 동향",
        "sources_master": _make_sources_master(["S1", "S2"]),
        "trend_name": {"value": "Some trend", "sources": ["S1"], "notes": ""},
        "definition": {"value": "Definition text", "sources": ["S1", "S2"], "notes": ""},
    }
    is_valid, errors = validate_source_references(schema)
    assert is_valid is True
    assert errors == []


def test_invalid_source_reference():
    schema = {
        "category": "해외 동향",
        "sources_master": _make_sources_master(["S1"]),
        "trend_name": {"value": "Some trend", "sources": ["S99"], "notes": ""},
    }
    is_valid, errors = validate_source_references(schema)
    assert is_valid is False
    assert any("S99" in e for e in errors)


def test_empty_value_with_invalid_source_is_ok():
    """Empty values should not trigger source reference errors."""
    schema = {
        "category": "해외 동향",
        "sources_master": _make_sources_master(["S1"]),
        "trend_name": {"value": "", "sources": ["S99"], "notes": ""},
    }
    is_valid, errors = validate_source_references(schema)
    # Empty value -> not checked
    assert is_valid is True


def test_nested_source_references():
    schema = {
        "sources_master": _make_sources_master(["S1", "S2"]),
        "core_change_structure": {
            "product_change": {"value": "change", "sources": ["S1"], "notes": ""},
            "consumption_change": {"value": "cons change", "sources": ["S999"], "notes": ""},
        },
    }
    is_valid, errors = validate_source_references(schema)
    assert is_valid is False
    assert any("S999" in e for e in errors)


def test_array_source_references():
    schema = {
        "sources_master": _make_sources_master(["S1"]),
        "background": [
            {"value": "bg1", "sources": ["S1"], "notes": ""},
            {"value": "bg2", "sources": ["S5"], "notes": ""},
        ],
    }
    is_valid, errors = validate_source_references(schema)
    assert is_valid is False
    assert any("S5" in e for e in errors)


def test_no_sources_master_all_empty_ok():
    """No sources_master and all values empty -> valid."""
    schema = {
        "sources_master": [],
        "trend_name": {"value": "", "sources": [], "notes": ""},
    }
    is_valid, errors = validate_source_references(schema)
    assert is_valid is True


def test_cases_array_source_validation():
    schema = {
        "sources_master": _make_sources_master(["S1"]),
        "cases": [
            {
                "company": {"value": "CompanyA", "sources": ["S1"], "notes": ""},
                "product_or_service": {"value": "ProdA", "sources": ["SINVALID"], "notes": ""},
                "how_it_works": {"value": "", "sources": [], "notes": ""},
                "features": [],
            }
        ],
    }
    is_valid, errors = validate_source_references(schema)
    assert is_valid is False
    assert any("SINVALID" in e for e in errors)
