import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent

load_dotenv(BASE_DIR / ".env")

def load_field_rules() -> dict:
    rules_path = BASE_DIR / "field_rules.json"
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)

FIELD_RULES = load_field_rules()

SUPPORTED_CATEGORIES = list(FIELD_RULES["categories"].keys())

GLOBAL_RULES = FIELD_RULES["global_rules"]
