"""Smoke tests showing the Live mock used the way the remote script uses Live."""
import pytest

Live = pytest.importorskip("Live")


def test_timer_matches_how_the_remote_script_creates_it():
    ticks = []
    timer = Live.Base.Timer(callback=lambda: ticks.append(1), interval=20, repeat=True)
    timer.start()
    timer.tick()
    assert ticks == [1]


def test_create_track_and_load_device(mock_live_session):
    song = mock_live_session
    track = song.create_midi_track()
    browser = Live.Application.get_application().browser
    item = next(i for i in browser.instruments.children if i.name == "Operator")
    browser.load_item(item)
    assert [d.name for d in track.devices] == ["Operator"]


def test_assert_on_calls_made(mock_live_session):
    mock_live_session.tempo = 128.0
    mock_live_session.start_playing()
    assert [(r.kind, r.name) for r in Live.call_log if r.name in ("tempo", "start_playing")] == [
        ("set", "tempo"), ("call", "start_playing")]
