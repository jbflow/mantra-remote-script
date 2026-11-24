"""
Example test demonstrating the use of LiveAPI-mock fixtures.

This shows how to test mantra-remote-script functionality using the mock
Ableton Live API without requiring a real Live instance.
"""

import pytest


def test_song_basic_operations(mock_live_session):
    """Test basic song operations using the mock Live API."""
    # Create a track
    track = mock_live_session.create_track("Bass")
    assert track.name == "Bass"
    assert len(mock_live_session.tracks) == 1

    # Create a clip
    from live import Clip
    clip = Clip("Intro")
    track.add_clip(clip)
    assert len(track.clips) == 1

    # Add notes to the clip
    clip.add_note(pitch=36, start_time=0.0, duration=0.5, velocity=100)
    clip.add_note(pitch=43, start_time=0.5, duration=0.5, velocity=100)
    assert len(clip.notes) == 2

    # Inspect API calls
    calls = mock_live_session.get_call_log()
    assert any(call[0] == "create_track" for call in calls)


def test_track_control(live_track):
    """Test track control using the fixture."""
    assert live_track.mute is False
    live_track.mute = True
    assert live_track.mute is True

    assert live_track.solo is False
    live_track.solo = True
    assert live_track.solo is True

    assert live_track.arm is False
    live_track.arm = True
    assert live_track.arm is True


def test_device_operations(mock_live_session, live_device):
    """Test device operations."""
    track = mock_live_session.create_track("Synth")
    track.add_device(live_device)

    assert len(track.devices) == 1
    assert track.get_device(0).name == "Test Device"


def test_song_playback(mock_live_session):
    """Test song playback control."""
    assert mock_live_session.is_playing is False
    assert mock_live_session.tempo == 120.0

    mock_live_session.play()
    assert mock_live_session.is_playing is True

    mock_live_session.set_tempo(140.0)
    assert mock_live_session.tempo == 140.0

    mock_live_session.stop()
    assert mock_live_session.is_playing is False


@pytest.mark.parametrize("bpm", [90, 100, 120, 140, 160])
def test_various_tempos(mock_live_session, bpm):
    """Test setting various tempo values."""
    mock_live_session.set_tempo(float(bpm))
    assert mock_live_session.tempo == float(bpm)
