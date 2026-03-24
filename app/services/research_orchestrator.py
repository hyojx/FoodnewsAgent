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
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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

        try:
            job = self._run(job)
        except ArticleParseError as e:
            job.status = "failed"
            job.error_code = e.code
            job.error_message = e.message
            job.finished_at = _now_iso()
            self.repo.update(job)
            return job
        except Exception as e:
            job.status = "failed"
            job.error_code = "SYS_001"
            job.error_message = str(e)
            job.finished_at = _now_iso()
            self.repo.update(job)
            return job

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
            queries = self._get_search_queries(job, topic, article, missing_fields)

            # Execute searches
            extra_results = []
            seen_urls = {s["url"] for s in filled_schema.get("sources_master", [])}
            for q in queries[:5]:
                for r in self.search_service.search(q, limit=3):
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        extra_results.append(r)

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
                )
                if queries:
                    return queries
            except Exception:
                pass

        # Fallback: rule-based queries per missing field
        queries = []
        for field_path in missing_fields[:5]:
            results = self.search_service._generate_queries(field_path, topic, job.category)
            queries.extend(results[:2])
        return queries
