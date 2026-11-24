import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def _reset_live():
    Live = pytest.importorskip("Live", reason="install LiveAPI-mock: pip install -e ../LiveAPI-mock")
    Live.reset()
    yield
    Live.reset()


@pytest.fixture
def mock_live_session():
    """A fresh mock Live Song (the same object Live.Application.get_application().get_document() returns)."""
    import Live
    return Live.Application.get_application().get_document()
