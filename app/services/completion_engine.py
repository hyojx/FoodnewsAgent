"""Completion engine: calculates completion_rate and detects missing fields.

Implements the field scoring rules from field_rules.json and reference.md:
  - 1.0 = value present + sources present + min_items met
  - 0.5 = value present but sources missing OR min_items partially met
  - 0.0 = empty / null value
"""
from typing import Any, Dict, List, Tuple

from app.config import FIELD_RULES


def _get_nested(obj: Dict, path: str) -> Any:
    """Navigate a dot-notated path in a dict. Returns None if path missing."""
    parts = path.split(".")
    cur = obj
    for part in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _score_value_with_sources(field_val: Any, must_have_sources: bool) -> float:
    if field_val is None:
        return 0.0
    value = field_val.get("value", "") if isinstance(field_val, dict) else ""
    sources = field_val.get("sources", []) if isinstance(field_val, dict) else []

    if not value or value.strip() == "":
        return 0.0
    if must_have_sources and len(sources) == 0:
        return 0.5
    return 1.0


def _score_array_of_value_with_sources(
    arr: Any, min_items: int, must_have_sources: bool
) -> float:
    if not isinstance(arr, list) or len(arr) == 0:
        return 0.0

    # Array length score
    if len(arr) < min_items:
        length_score = 0.5
    else:
        length_score = 1.0

    # Check each item has value + sources
    valid_items = sum(
        1
        for item in arr
        if isinstance(item, dict)
        and item.get("value", "").strip()
        and (not must_have_sources or len(item.get("sources", [])) > 0)
    )
    if len(arr) > 0 and valid_items < len(arr):
        item_score = valid_items / len(arr)
    else:
        item_score = 1.0

    return min(length_score, item_score if item_score < 1.0 else length_score)


def _score_array(arr: Any, min_items: int, must_have_sources: bool, schema: Dict) -> float:
    """Score a top-level array field like cases[] or applications[]."""
    if not isinstance(arr, list) or len(arr) == 0:
        return 0.0
    if len(arr) < min_items:
        return 0.5
    return 1.0


def score_field(
    field_rule: Dict,
    schema: Dict,
    category: str,
) -> Tuple[float, str]:
    """Return (score, status) for a single field rule.

    status: 'complete' | 'partial' | 'missing'
    """
    field_path = field_rule["field_path"]
    field_type = field_rule["type"]
    must_have_sources = field_rule.get("must_have_sources", False)
    min_items = field_rule.get("min_items", 1)

    # Handle nested array item fields like cases[].company or cases[].features
    if "[]." in field_path:
        parent_path, sub_field = field_path.split("[].", 1)
        parent_arr = _get_nested(schema, parent_path)
        if not isinstance(parent_arr, list) or len(parent_arr) == 0:
            score = 0.0
        else:
            sub_scores = []
            for item in parent_arr:
                if isinstance(item, dict):
                    sub_val = item.get(sub_field)
                    if field_type == "array_of_value_with_sources":
                        sub_scores.append(
                            _score_array_of_value_with_sources(sub_val, min_items, must_have_sources)
                        )
                    else:
                        sub_scores.append(
                            _score_value_with_sources(sub_val, must_have_sources)
                        )
            score = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
    elif field_type == "string":
        val = _get_nested(schema, field_path)
        score = 1.0 if (val and str(val).strip()) else 0.0
    elif field_type == "datetime":
        val = _get_nested(schema, field_path)
        score = 1.0 if (val and str(val).strip()) else 0.0
    elif field_type == "array":
        arr = _get_nested(schema, field_path)
        score = _score_array(arr, min_items, must_have_sources, schema)
    elif field_type == "value_with_sources":
        val = _get_nested(schema, field_path)
        score = _score_value_with_sources(val, must_have_sources)
    elif field_type == "array_of_value_with_sources":
        arr = _get_nested(schema, field_path)
        score = _score_array_of_value_with_sources(arr, min_items, must_have_sources)
    else:
        val = _get_nested(schema, field_path)
        score = 1.0 if val is not None else 0.0

    if score >= 1.0:
        status = "complete"
    elif score > 0.0:
        status = "partial"
    else:
        status = "missing"

    return score, status


def calculate_completion_rate(category: str, schema: Dict) -> Tuple[float, List[str], Dict[str, float]]:
    """Calculate weighted completion_rate for a filled schema.

    Returns:
        (completion_rate, missing_fields, field_scores)
    """
    category_rules = FIELD_RULES["categories"].get(category)
    if not category_rules:
        raise ValueError(f"No rules for category: {category}")

    fields = category_rules["fields"]
    total_weight = 0.0
    earned_weight = 0.0
    missing_fields = []
    field_scores = {}

    for rule in fields:
        field_path = rule["field_path"]
        weight = rule.get("weight", 1.0)
        score, status = score_field(rule, schema, category)

        total_weight += weight
        earned_weight += score * weight
        field_scores[field_path] = score

        if status != "complete":
            missing_fields.append(field_path)

    completion_rate = earned_weight / total_weight if total_weight > 0 else 0.0
    return round(completion_rate, 4), missing_fields, field_scores


def determine_status(completion_rate: float, category: str) -> str:
    thresholds = FIELD_RULES["categories"][category]["completion_thresholds"]
    completed_threshold = thresholds["completed"]
    partial_threshold = thresholds["partial_completed"]

    if completion_rate >= completed_threshold:
        return "completed"
    elif completion_rate >= partial_threshold:
        return "partial_completed"
    else:
        return "failed"
