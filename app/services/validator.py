"""Validator service.

Validates that all source references in a filled schema point to valid
source_ids from sources_master. Enforces the PRD rule:
  "all non-empty researched values must reference valid source_ids from sources_master"
"""
from typing import Any, Dict, List, Tuple


def _collect_source_ids(sources_master: List[Dict]) -> set:
    return {s["source_id"] for s in sources_master if isinstance(s, dict) and "source_id" in s}


def _walk_value_with_sources(
    obj: Any, path: str, valid_ids: set, errors: List[str]
) -> None:
    if isinstance(obj, dict):
        if "value" in obj and "sources" in obj:
            value = obj.get("value", "")
            sources = obj.get("sources", [])
            if value and value.strip():
                for sid in sources:
                    if sid not in valid_ids:
                        errors.append(
                            f"Field '{path}' references invalid source_id '{sid}'"
                        )
        else:
            for k, v in obj.items():
                _walk_value_with_sources(v, f"{path}.{k}" if path else k, valid_ids, errors)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _walk_value_with_sources(item, f"{path}[{i}]", valid_ids, errors)


def validate_source_references(schema: Dict) -> Tuple[bool, List[str]]:
    """Check that all non-empty field values reference valid source_ids.

    Returns (is_valid, list_of_error_messages).
    """
    sources_master = schema.get("sources_master", [])
    valid_ids = _collect_source_ids(sources_master)

    errors: List[str] = []

    # Walk all fields except sources_master itself
    for key, val in schema.items():
        if key == "sources_master":
            continue
        _walk_value_with_sources(val, key, valid_ids, errors)

    return len(errors) == 0, errors


def validate_request_schema(request_data: Dict) -> Tuple[bool, List[str]]:
    """Basic request validation beyond Pydantic field checks."""
    errors = []
    article_url = request_data.get("article_url", "")
    if not article_url:
        errors.append("article_url is required")
    category = request_data.get("category", "")
    if not category:
        errors.append("category is required")
    return len(errors) == 0, errors
