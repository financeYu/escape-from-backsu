from __future__ import annotations

import sys
from pathlib import Path
import shutil
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def sample_paper():
    return _sample_paper


def _sample_paper(**overrides):
    from research_ingestion.normalize import make_normalized_paper

    payload = {
        "title": "Daily momentum and reversal in equity returns",
        "source_adapter": "fixture",
        "authors": ["Jane Doe"],
        "doi": "10.1000/example",
        "publication_year": 2024,
        "publication_date": "2024-01-01",
        "venue": "Journal of Tests",
        "abstract": "We study daily returns, momentum, reversal, transaction costs, and define a transparent signal.",
        "source_urls": ["https://doi.org/10.1000/example"],
        "oa_status": "open",
        "license": "cc-by",
        "is_retracted": False,
        "citation_count": 123,
        "topics": ["Momentum"],
        "fields_of_study": ["Finance"],
    }
    payload.update(overrides)
    return make_normalized_paper(**payload)


@pytest.fixture
def workspace_tmp_path(request):
    name = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in request.node.name)
    path = PROJECT_ROOT / "tests" / "_tmp" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    yield path
    if path.exists():
        shutil.rmtree(path)
