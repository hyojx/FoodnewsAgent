"""In-memory repository for research jobs.

This is intentionally simple for MVP. The interface is designed so it can
be swapped for a PostgreSQL-backed implementation without changing service code.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class ResearchJob:
    request_id: str
    article_url: str
    category: str
    status: str  # queued | processing | completed | partial_completed | failed
    options: Dict[str, Any]
    target_schema: Optional[Dict[str, Any]] = None

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    completion_rate: float = 0.0
    iterations_count: int = 0
    missing_fields: List[str] = field(default_factory=list)
    filled_schema: Optional[Dict[str, Any]] = None
    sources_used: int = 0

    error_code: Optional[str] = None
    error_message: Optional[str] = None


class ResearchRepository:
    def __init__(self):
        self._store: Dict[str, ResearchJob] = {}

    def create(self, job: ResearchJob) -> ResearchJob:
        self._store[job.request_id] = job
        return job

    def get(self, request_id: str) -> Optional[ResearchJob]:
        return self._store.get(request_id)

    def update(self, job: ResearchJob) -> ResearchJob:
        self._store[job.request_id] = job
        return job

    def list_all(self) -> List[ResearchJob]:
        return list(self._store.values())

    def clear(self):
        """Used in tests to reset state between test cases."""
        self._store.clear()


# Singleton repository instance
_repo = ResearchRepository()


def get_repo() -> ResearchRepository:
    return _repo
