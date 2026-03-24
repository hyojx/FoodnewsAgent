import os
import pytest

# Force stub extractor so tests don't need ANTHROPIC_API_KEY
os.environ["USE_STUB_EXTRACTOR"] = "true"

from fastapi.testclient import TestClient
from app.main import app
from app.repositories.research_repo import get_repo


@pytest.fixture(autouse=True)
def clear_repo():
    get_repo().clear()
    yield
    get_repo().clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
