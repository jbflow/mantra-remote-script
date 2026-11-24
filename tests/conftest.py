"""
Pytest configuration and fixtures for mantra-remote-script tests.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path so we can import mantra modules
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="function")
def mock_live_session():
    """
    Pytest fixture that provides a fresh Song instance for testing.

    This uses the LiveAPI-mock library to provide mock Ableton Live objects
    without requiring a running Live instance. Perfect for unit testing
    remote script functionality in CI/CD.

    Example:
        def test_track_control(mock_live_session):
            track = mock_live_session.create_track("Test Track")
            assert track.name == "Test Track"
    """
    try:
        from live import Song
    except ImportError:
        pytest.skip("live module not available - install LiveAPI-mock")

    song = Song()
    yield song
    song.reset()


@pytest.fixture(scope="function")
def live_song():
    """Alias for mock_live_session for compatibility."""
    try:
        from live import Song
    except ImportError:
        pytest.skip("live module not available - install LiveAPI-mock")

    song = Song()
    yield song
    song.reset()


@pytest.fixture(scope="function")
def live_track(mock_live_session):
    """Fixture that provides a track in a mock Live session."""
    return mock_live_session.create_track("Test Track")


@pytest.fixture(scope="function")
def live_clip():
    """Fixture that provides a mock Live clip."""
    try:
        from live import Clip
    except ImportError:
        pytest.skip("live module not available - install LiveAPI-mock")

    return Clip("Test Clip")


@pytest.fixture(scope="function")
def live_device():
    """Fixture that provides a mock Live device."""
    try:
        from live import Device
    except ImportError:
        pytest.skip("live module not available - install LiveAPI-mock")

    return Device("Test Device")
