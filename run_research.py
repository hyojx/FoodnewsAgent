"""CLI script to run a research job and save results to a JSON file.

Usage:
    python run_research.py <article_url> <category>

Categories:
    "해외 동향"
    "상품·서비스"
    "푸드테크"

Example:
    python run_research.py "https://prtimes.jp/..." "상품·서비스"
"""
import sys
import json
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.repositories.research_repo import ResearchJob, ResearchRepository
from app.services.research_orchestrator import ResearchOrchestrator


def main():
    if len(sys.argv) < 3:
        print("Usage: python run_research.py <article_url> <category>")
        print('Categories: "해외 동향" | "상품·서비스" | "푸드테크"')
        sys.exit(1)

    article_url = sys.argv[1]
    category = sys.argv[2]

    supported = ["해외 동향", "상품·서비스", "푸드테크"]
    if category not in supported:
        print(f"❌ Unsupported category: {category}")
        print(f"   Supported: {supported}")
        sys.exit(1)

    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable is not set.")
        print("   Export it: export OPENAI_API_KEY=sk-...")
        sys.exit(1)

    repo = ResearchRepository()
    request_id = f"req_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    job = ResearchJob(
        request_id=request_id,
        article_url=article_url,
        category=category,
        status="queued",
        options={
            "max_iterations": 3,
            "min_completion_rate": 0.85,
            "search_limit_per_iteration": 5,
        },
    )
    repo.create(job)

    print(f"🔍 Starting research...")
    print(f"   URL     : {article_url}")
    print(f"   Category: {category}")
    print(f"   Job ID  : {request_id}")
    print(f"   Model   : gpt-4o")
    print()

    orchestrator = ResearchOrchestrator()
    orchestrator.repo = repo

    print("📰 Step 1: Fetching article...")
    job = orchestrator.process(job)

    if job.status == "failed":
        print(f"\n❌ Failed: [{job.error_code}] {job.error_message}")
        sys.exit(1)

    # Build output
    output = {
        "request_id": job.request_id,
        "status": job.status,
        "category": job.category,
        "article_url": job.article_url,
        "completion_rate": job.completion_rate,
        "iterations_count": job.iterations_count,
        "sources_used": job.sources_used,
        "missing_fields": job.missing_fields,
        "result": {
            "filled_schema": job.filled_schema,
            "missing_fields": job.missing_fields,
            "sources_used": job.sources_used,
        },
        "meta": {
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        },
        "error": (
            {"code": job.error_code, "message": job.error_message}
            if job.error_code else None
        ),
    }

    # Save to results/
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_category = category.replace("·", "_").replace(" ", "_")
    filename = f"{timestamp}_{safe_category}.json"
    output_path = results_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done! Status     : {job.status}")
    print(f"   Completion rate : {job.completion_rate:.0%}")
    print(f"   Iterations      : {job.iterations_count}")
    print(f"   Sources used    : {job.sources_used}")
    if job.missing_fields:
        print(f"   Missing fields  : {job.missing_fields}")
    print(f"\n📄 Result saved to:\n   {output_path}")


if __name__ == "__main__":
    main()
