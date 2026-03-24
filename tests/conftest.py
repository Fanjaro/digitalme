"""Shared test fixtures for DigitalMe tests."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "skills" / "data"
META_DIR = ROOT / "skills" / "meta"


@pytest.fixture
def data_dir():
    return DATA_DIR


@pytest.fixture
def meta_dir():
    return META_DIR


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def load_data():
    """Return a loader function for skills/data/ files."""
    def _loader(filename: str) -> dict:
        return _load_json(DATA_DIR / filename)
    return _loader


@pytest.fixture
def load_meta():
    """Return a loader function for skills/meta/ files."""
    def _loader(filename: str) -> dict:
        return _load_json(META_DIR / filename)
    return _loader


@pytest.fixture
def mock_user_meta():
    """Return mock meta for 张明远."""
    from mock_data import MOCK_USER_META
    return MOCK_USER_META.copy()


@pytest.fixture
def mock_dim_results():
    """Return all mock dimension results."""
    from mock_data import MOCK_DIMENSION_RESULTS
    return MOCK_DIMENSION_RESULTS.copy()


@pytest.fixture
def sample_graph_state():
    """Return a minimal graph state for testing."""
    return {
        "user_sample_id": "CD888888",
        "user_meta": None,
        "target_dimensions": [],
        "dimension_results": [],
        "synthesized_report": None,
    }
