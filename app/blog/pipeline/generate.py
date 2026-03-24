"""Outline Generator and Draft Writer agents."""
from typing import Any, Dict

from app.blog.pipeline.llm import get_llm_client, parse_json_response, MODEL, MAX_TOKENS_JSON, MAX_TOKENS_TEXT
from app.blog.prompts.outline import SYSTEM_OUTLINE, build_outline_prompt
from app.blog.prompts.draft import SYSTEM_DRAFT, build_draft_prompt
from app.blog.schemas.outline import OutlineJSON, OutlineSection
from app.blog.templates import get_template


class OutlineGenerator:
    """Agent 1: Generates structured outline from normalized article JSON."""

    def generate(self, article_json: Dict[str, Any]) -> OutlineJSON:
        category = article_json.get("category", "")
        template = get_template(category)

        client = get_llm_client()
        prompt = build_outline_prompt(article_json, template)

        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS_JSON,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_OUTLINE},
                {"role": "user", "content": prompt},
            ],
        )

        text = response.choices[0].message.content or ""
        fallback_raw = {
            "title": "",
            "lead_angle": "",
            "sections": [{"heading": h, "points": []} for h in template.sections],
            "evidence_map": template.evidence_map,
        }
        raw = parse_json_response(text, fallback_raw)

        return self._build_outline(raw, template)

    def _build_outline(self, raw: dict, template) -> OutlineJSON:
        sections_raw = raw.get("sections", [])
        sections = [
            OutlineSection(
                heading=s.get("heading", ""),
                points=[str(p) for p in s.get("points", [])],
            )
            for s in sections_raw
            if isinstance(s, dict)
        ]

        # Clamp to 4-6 sections; pad from template if too few
        if len(sections) < 4:
            for i in range(len(sections), len(template.sections)):
                sections.append(OutlineSection(heading=template.sections[i], points=[]))
            sections = sections[:6]

        sections = sections[:6]

        evidence_map = raw.get("evidence_map") or template.evidence_map

        return OutlineJSON(
            title=raw.get("title", ""),
            lead_angle=raw.get("lead_angle", ""),
            sections=sections,
            evidence_map=evidence_map,
        )


class DraftWriter:
    """Agent 2: Writes Korean industry-report style blog post from outline + JSON."""

    def write(self, article_json: Dict[str, Any], outline: OutlineJSON) -> str:
        client = get_llm_client()
        prompt = build_draft_prompt(article_json, outline)

        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS_TEXT,
            messages=[
                {"role": "system", "content": SYSTEM_DRAFT},
                {"role": "user", "content": prompt},
            ],
        )

        return response.choices[0].message.content or ""
