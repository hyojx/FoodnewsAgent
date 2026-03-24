"""Tests for completion_rate calculation and status determination."""
import pytest
from app.services.completion_engine import calculate_completion_rate, determine_status


def _vws(value="", sources=None, notes=""):
    return {"value": value, "sources": sources or [], "notes": notes}


def _make_source(sid):
    return {
        "source_id": sid,
        "url": f"https://example.com/{sid}",
        "title": f"Article {sid}",
        "publisher": "Test",
        "published_at": "2026-03-24",
        "source_type": "article",
        "is_duplicate": False,
    }


# ─── 해외 동향 ────────────────────────────────────────────────────────────────

def _full_overseas_schema():
    s1, s2 = "S1", "S2"
    return {
        "category": "해외 동향",
        "topic": "Test Topic",
        "researched_at": "2026-03-24",
        "sources_master": [_make_source(s1), _make_source(s2)],
        "trend_name": _vws("Trend Name", [s1]),
        "definition": _vws("Definition.", [s1, s2]),
        "change_from_previous": _vws("Change.", [s1]),
        "background": [_vws("Background.", [s1])],
        "core_change_structure": {
            "product_change": _vws("Product change.", [s1]),
            "consumption_change": _vws("Consumption change.", [s1]),
        },
        "cases": [
            {
                "company": _vws("CompanyA", [s1]),
                "product_or_service": _vws("ProdA", [s1]),
                "how_it_works": _vws("How A works.", [s1]),
                "features": [_vws("Feature A1", [s1])],
            },
            {
                "company": _vws("CompanyB", [s2]),
                "product_or_service": _vws("ProdB", [s2]),
                "how_it_works": _vws("How B works.", [s2]),
                "features": [_vws("Feature B1", [s2])],
            },
        ],
        "expansion_pattern": {
            "geographic_scope": _vws("Asia, Europe.", [s1]),
            "industry_expansion": _vws("F&B, retail.", [s1]),
        },
    }


def test_overseas_full_schema_high_completion():
    schema = _full_overseas_schema()
    rate, missing, _ = calculate_completion_rate("해외 동향", schema)
    assert rate >= 0.85, f"Expected high completion, got {rate}"
    assert missing == [] or len(missing) == 0


def test_overseas_empty_schema_low_completion():
    schema = {
        "category": "해외 동향",
        "topic": "",
        "researched_at": "",
        "sources_master": [],
        "trend_name": _vws(),
        "definition": _vws(),
        "change_from_previous": _vws(),
        "background": [],
        "core_change_structure": {"product_change": _vws(), "consumption_change": _vws()},
        "cases": [],
        "expansion_pattern": {"geographic_scope": _vws(), "industry_expansion": _vws()},
    }
    rate, missing, _ = calculate_completion_rate("해외 동향", schema)
    assert rate < 0.6
    assert len(missing) > 0


def test_overseas_partial_missing_sources():
    schema = _full_overseas_schema()
    # Remove sources from several fields
    schema["trend_name"]["sources"] = []
    schema["definition"]["sources"] = []
    rate, missing, _ = calculate_completion_rate("해외 동향", schema)
    # Should be partial but not 0
    assert 0.0 < rate < 1.0
    assert "trend_name" in missing or "definition" in missing


def test_overseas_only_one_case_partial():
    schema = _full_overseas_schema()
    schema["cases"] = schema["cases"][:1]  # Only 1 case instead of 2
    rate, missing, _ = calculate_completion_rate("해외 동향", schema)
    # cases requires min 2, so should be partial
    assert "cases" in missing


# ─── 상품·서비스 ──────────────────────────────────────────────────────────────

def _full_product_service_schema():
    s1 = "S1"
    return {
        "category": "상품·서비스",
        "topic": "Test Product",
        "researched_at": "2026-03-24",
        "sources_master": [_make_source(s1)],
        "name": _vws("ProductX", [s1]),
        "summary": _vws("Summary of ProductX.", [s1]),
        "developer": {
            "company_name": _vws("DevCo", [s1]),
            "company_description": _vws("DevCo builds things.", [s1]),
        },
        "purpose": _vws("Product purpose.", [s1]),
        "key_features": [_vws("Feature1", [s1]), _vws("Feature2", [s1])],
        "how_it_works": _vws("How it works.", [s1]),
        "data_or_technology_basis": [_vws("Tech basis.", [s1])],
        "business_model": {
            "pricing": _vws("비공개", [s1]),
            "model": _vws("SaaS", [s1]),
        },
        "use_effects": [_vws("Effect1.", [s1])],
        "differentiation": _vws("Unique differentiation.", [s1]),
    }


def test_product_service_full_schema_high_completion():
    schema = _full_product_service_schema()
    rate, missing, _ = calculate_completion_rate("상품·서비스", schema)
    assert rate >= 0.85, f"Expected high completion, got {rate}"


def test_product_service_missing_key_features_min():
    schema = _full_product_service_schema()
    schema["key_features"] = [_vws("Only one feature", ["S1"])]  # min is 2
    rate, missing, _ = calculate_completion_rate("상품·서비스", schema)
    assert "key_features" in missing


# ─── 푸드테크 ──────────────────────────────────────────────────────────────────

def _full_foodtech_schema():
    s1 = "S1"
    return {
        "category": "푸드테크",
        "topic": "FoodTech Test",
        "researched_at": "2026-03-24",
        "sources_master": [_make_source(s1)],
        "technology_name": _vws("TechA", [s1]),
        "summary": _vws("Summary of TechA.", [s1]),
        "technology_principle": _vws("The principle of TechA.", [s1]),
        "problem_with_existing_method": _vws("Existing problem.", [s1]),
        "solution": _vws("TechA solution.", [s1]),
        "applications": [
            {
                "company": _vws("FoodCo", [s1]),
                "application_form": _vws("Use in packaging.", [s1]),
            }
        ],
        "results_and_effects": [_vws("30% cost reduction.", [s1])],
        "use_cases": [_vws("Retail use case.", [s1])],
        "industry_meaning": _vws("Industry significance.", [s1]),
    }


def test_foodtech_full_schema_high_completion():
    schema = _full_foodtech_schema()
    rate, missing, _ = calculate_completion_rate("푸드테크", schema)
    assert rate >= 0.85, f"Expected high completion, got {rate}"


def test_foodtech_empty_applications():
    schema = _full_foodtech_schema()
    schema["applications"] = []
    rate, missing, _ = calculate_completion_rate("푸드테크", schema)
    assert "applications" in missing


# ─── Status determination ────────────────────────────────────────────────────

def test_status_completed():
    status = determine_status(0.90, "해외 동향")
    assert status == "completed"


def test_status_partial_completed():
    status = determine_status(0.72, "해외 동향")
    assert status == "partial_completed"


def test_status_failed():
    status = determine_status(0.40, "해외 동향")
    assert status == "failed"


def test_status_at_completed_threshold():
    status = determine_status(0.85, "해외 동향")
    assert status == "completed"


def test_status_at_partial_threshold():
    status = determine_status(0.60, "해외 동향")
    assert status == "partial_completed"


def test_status_below_partial_threshold():
    status = determine_status(0.59, "해외 동향")
    assert status == "failed"
