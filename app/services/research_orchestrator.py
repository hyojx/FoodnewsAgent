"""Research orchestrator.

Coordinates the full research loop:
  1. Parse article
  2. Extract schema with LLM (iteration 1)
  3. Detect missing fields
  4. Generate search queries for missing fields (LLM)
  5. Search + fetch new sources
  6. Merge new sources into schema (LLM) (iterations 2..N)
  7. Validate and return result
"""
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import FIELD_RULES
from app.repositories.research_repo import ResearchJob, get_repo
from app.services.article_parser import ArticleParser, ArticleParseError
from app.services.search_service import SearchService
from app.services.extractor import extract
from app.services.completion_engine import calculate_completion_rate, determine_status
from app.services.validator import validate_source_references

_USE_STUB = os.environ.get("USE_STUB_EXTRACTOR", "").lower() in ("1", "true", "yes")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Generic Korean words that do NOT indicate topic relevance
_GENERIC_KO = frozenset({
    "신상품", "제품", "브랜드", "기업", "사례", "정의", "트렌드", "이란", "특징",
    "배경", "역사", "가격", "요금", "업계", "의의", "영향", "방법", "작동",
    "기능", "원리", "기술", "활용", "응용", "결과", "효과", "실적",
})


def _filter_by_relevance(results: list, article_title: str, topic: str) -> list:
    """Keep results that share at least one meaningful keyword with the article/topic.

    Falls back to the full list if filtering removes everything.
    """
    combined_text = f"{article_title} {topic}"
    # Extract Korean words (2+ chars) and ASCII words (3+ chars)
    ko_words = set(re.findall(r'[가-힣]{2,}', combined_text))
    en_words = set(w.lower() for w in re.findall(r'[a-zA-Z]{3,}', combined_text))
    keywords = (ko_words | en_words) - _GENERIC_KO

    if not keywords:
        return results

    filtered = []
    for r in results:
        haystack = f"{r.title} {r.snippet} {r.full_content[:300]}".lower()
        if any(kw.lower() in haystack for kw in keywords):
            filtered.append(r)

    return filtered if filtered else results


class ResearchOrchestrator:
    def __init__(
        self,
        article_parser: Optional[ArticleParser] = None,
        search_service: Optional[SearchService] = None,
    ):
        self.article_parser = article_parser or ArticleParser()
        self.search_service = search_service or SearchService()
        self.repo = get_repo()

    def process(self, job: ResearchJob) -> ResearchJob:
        job.status = "processing"
        job.started_at = _now_iso()
        self.repo.update(job)
        logging.info("[JOB %s] status=processing category=%s", job.request_id, job.category)

        try:
            job = self._run(job)
        except ArticleParseError as e:
            job.status = "failed"
            job.error_code = e.code
            job.error_message = e.message
            job.finished_at = _now_iso()
            self.repo.update(job)
            logging.error("[JOB %s] status=failed error=%s %s", job.request_id, e.code, e.message)
            return job
        except Exception as e:
            job.status = "failed"
            job.error_code = "SYS_001"
            job.error_message = str(e)
            job.finished_at = _now_iso()
            self.repo.update(job)
            logging.error("[JOB %s] status=failed error=SYS_001 %s", job.request_id, str(e))
            return job

        logging.info(
            "[JOB %s] status=%s completion_rate=%.2f iterations=%d missing=%s",
            job.request_id, job.status, job.completion_rate or 0.0,
            job.iterations_count, job.missing_fields or [],
        )
        return job

    def _run(self, job: ResearchJob) -> ResearchJob:
        options = job.options
        max_iterations = options.get("max_iterations", FIELD_RULES["global_rules"]["default_max_iterations"])
        min_completion_rate = options.get("min_completion_rate", FIELD_RULES["global_rules"]["default_min_completion_rate"])
        min_sources_required = options.get("min_sources_required", FIELD_RULES["global_rules"].get("min_sources_required", 3))

        # Step 1: Parse article
        article = self.article_parser.parse(job.article_url)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Step 2: Initial LLM extraction from article
        filled_schema = extract(
            category=job.category,
            article=article,
            search_results=[],
            existing_schema=job.target_schema,
            researched_at=today,
            is_initial=True,
        )

        completion_rate, missing_fields, _ = calculate_completion_rate(job.category, filled_schema)
        job.iterations_count = 1

        prev_missing_count = len(missing_fields)
        stagnant_iterations = 0

        # Steps 3-6: Iterative completion loop
        for iteration in range(2, max_iterations + 1):
            sources_so_far = len(filled_schema.get("sources_master", []))
            if completion_rate >= min_completion_rate and sources_so_far >= min_sources_required:
                break
            if not missing_fields and sources_so_far >= min_sources_required:
                break

            # Generate search queries for missing fields (LLM or rule-based)
            topic = filled_schema.get("topic", article.title)
            queries = self._get_search_queries(job, topic, article, missing_fields, article.language)

            # Execute searches
            extra_results = []
            seen_urls = {s["url"] for s in filled_schema.get("sources_master", [])}
            for q in queries[:5]:
                for r in self.search_service.search(q, limit=3, language=article.language):
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        extra_results.append(r)

            # Drop results unrelated to the article topic
            extra_results = _filter_by_relevance(extra_results, article.title, topic)

            if not extra_results:
                stagnant_iterations += 1
                if stagnant_iterations >= 2:
                    break
                continue

            # Merge new sources into schema
            filled_schema = extract(
                category=job.category,
                article=article,
                search_results=extra_results,
                existing_schema=filled_schema,
                researched_at=today,
                is_initial=False,
            )

            new_completion_rate, new_missing_fields, _ = calculate_completion_rate(job.category, filled_schema)
            job.iterations_count = iteration

            if len(new_missing_fields) >= prev_missing_count:
                stagnant_iterations += 1
            else:
                stagnant_iterations = 0

            completion_rate = new_completion_rate
            missing_fields = new_missing_fields
            prev_missing_count = len(missing_fields)

            if stagnant_iterations >= 2:
                break

        # Validate source references
        validate_source_references(filled_schema)

        final_status = determine_status(completion_rate, job.category)
        sources_used = len(filled_schema.get("sources_master", []))

        job.filled_schema = filled_schema
        job.completion_rate = completion_rate
        job.missing_fields = missing_fields
        job.sources_used = sources_used
        job.status = final_status
        job.finished_at = _now_iso()

        self.repo.update(job)
        return job

    def _get_search_queries(
        self,
        job: ResearchJob,
        topic: str,
        article: Any,
        missing_fields: list,
        language: str = "en",
    ) -> list:
        """Generate search queries: use LLM if available, else rule-based fallback."""
        if not _USE_STUB:
            try:
                from app.services.llm_extractor import generate_search_queries
                queries = generate_search_queries(
                    category=job.category,
                    topic=topic,
                    article_title=article.title,
                    missing_fields=missing_fields[:6],
                    limit_per_field=2,
                    article_language=language,
                )
                if queries:
                    return queries
            except Exception:
                pass

        # Fallback: rule-based queries per missing field
        queries = []
        for field_path in missing_fields[:5]:
            results = self.search_service._generate_queries(field_path, topic, job.category, article.title, language)
            queries.extend(results[:2])
        return queries

    def process_additional(self, job: ResearchJob) -> ResearchJob:
        """Process additional research on top of an existing filled schema."""
        job.status = "processing"
        job.started_at = _now_iso()
        self.repo.update(job)
        logging.info("[JOB %s] status=processing (additional) category=%s", job.request_id, job.category)

        try:
            job = self._run_additional(job)
        except Exception as e:
            job.status = "failed"
            job.error_code = "SYS_001"
            job.error_message = str(e)
            job.finished_at = _now_iso()
            self.repo.update(job)
            logging.error("[JOB %s] status=failed (additional) error=SYS_001 %s", job.request_id, str(e))
            return job

        logging.info(
            "[JOB %s] status=%s (additional) completion_rate=%.2f",
            job.request_id, job.status, job.completion_rate or 0.0,
        )
        return job

    def _run_additional(self, job: ResearchJob) -> ResearchJob:
        options = job.options
        additional_query: str = options.get("additional_query", "")
        filled_schema: dict = job.target_schema or {}

        # Detect article language from S1 in sources_master
        sources_master = filled_schema.get("sources_master", [])
        article_language = sources_master[0].get("language", "en") if sources_master else "en"
        topic = filled_schema.get("topic", "")

        # Generate search queries from natural language request
        queries: list = []
        if not _USE_STUB:
            try:
                from app.services.llm_extractor import generate_additional_queries
                queries = generate_additional_queries(
                    filled_schema=filled_schema,
                    additional_query=additional_query,
                    article_language=article_language,
                )
            except Exception:
                pass

        if not queries:
            # Fallback: use the raw query as a search string with topic as anchor
            queries = [f"{topic} {additional_query}"]

        # Execute searches
        extra_results = []
        seen_urls = {s["url"] for s in sources_master}
        for q in queries[:8]:
            for r in self.search_service.search(q, limit=3, language=article_language):
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    extra_results.append(r)

        # Drop results unrelated to the topic
        original_title = sources_master[0].get("title", "") if sources_master else ""
        extra_results = _filter_by_relevance(extra_results, original_title, topic)

        # Merge new sources into existing schema
        if extra_results and not _USE_STUB:
            from app.services.llm_extractor import merge_sources
            filled_schema = merge_sources(
                category=job.category,
                current_schema=filled_schema,
                new_results=extra_results,
                missing_fields=[additional_query],
            )

        validate_source_references(filled_schema)

        completion_rate, missing_fields, _ = calculate_completion_rate(job.category, filled_schema)
        final_status = determine_status(completion_rate, job.category)

        job.filled_schema = filled_schema
        job.completion_rate = completion_rate
        job.missing_fields = missing_fields
        job.sources_used = len(filled_schema.get("sources_master", []))
        job.iterations_count = 1
        job.status = final_status
        job.finished_at = _now_iso()
        self.repo.update(job)
        return job
