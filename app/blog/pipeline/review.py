"""Review Agent — validates and revises blog draft."""
from typing import Any, Dict

from app.blog.pipeline.llm import get_llm_client, parse_json_response, MODEL, MAX_TOKENS_TEXT
from app.blog.prompts.review import SYSTEM_REVIEW, build_review_prompt
from app.blog.schemas.outline import OutlineJSON
from app.blog.schemas.review import ReviewResult, ReviewIssue


class ReviewAgent:
    """Agent 3: Validates draft for factuality, structure, tone, and readability."""

    def review(
        self,
        article_json: Dict[str, Any],
        outline: OutlineJSON,
        draft: str,
    ) -> ReviewResult:
        client = get_llm_client()
        prompt = build_review_prompt(article_json, outline, draft)

        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS_TEXT,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_REVIEW},
                {"role": "user", "content": prompt},
            ],
        )

        text = response.choices[0].message.content or ""
        fallback = {"pass": False, "issues": [], "revised_draft": draft}
        raw = parse_json_response(text, fallback)

        return self._build_result(raw, draft)

    def _build_result(self, raw: dict, fallback_draft: str) -> ReviewResult:
        passed = bool(raw.get("pass", False))
        issues_raw = raw.get("issues", [])
        issues = [
            ReviewIssue(
                type=str(issue.get("type", "unknown")),
                text=str(issue.get("text", "")),
                reason=str(issue.get("reason", "")),
            )
            for issue in issues_raw
            if isinstance(issue, dict)
        ]
        revised_draft = raw.get("revised_draft") or fallback_draft

        return ReviewResult(
            passed=passed,
            issues=issues,
            revised_draft=revised_draft,
        )
