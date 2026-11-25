"""Performance actions against the Live mock: firing scenes and clips."""
import pytest

Live = pytest.importorskip("Live")


def calls(name, target=None):
    return [r for r in Live.call_log if r.name == name and (target is None or r.target == target)]


def test_trigger_scene_by_name(song, ok, named_track):
    drums = named_track('Drums')
    song.create_scene(-1)
    chorus = song.create_scene(-1)
    chorus.name = 'Chorus'
    drums.clip_slots[0].create_clip(4)
    drums.clip_slots[1].create_clip(4)
    ok('performance', 'trigger_scene', scene_name='chorus')
    assert len(calls('fire', 'Scene')) == 1
    assert drums.clip_slots[1].is_playing and not drums.clip_slots[0].is_playing


def test_trigger_scene_by_number(song, ok, named_track):
    named_track('Drums')
    first = song.create_scene(-1)
    song.create_scene(-1)
    first.clip_slots[0].create_clip(4)
    ok('performance', 'trigger_scene', scene_name=1)
    assert first.clip_slots[0].is_playing


def test_trigger_unknown_scene(song, run):
    song.create_scene(-1)
    assert run('performance', 'trigger_scene', scene_name='Nope')['status'] == 'error'
    assert not calls('fire')


def test_trigger_clip_by_name(song, ok, named_track):
    named_track('Other')
    drums = named_track('Drums')
    song.create_scene(-1)
    song.create_scene(-1)
    drums.clip_slots[1].create_clip(4)
    drums.clip_slots[1].clip.name = 'Fill'
    ok('performance', 'trigger_clip', target={'role': 'drums'}, clip_name='fill')
    assert drums.clip_slots[1].is_playing
    assert not drums.clip_slots[0].is_playing


def test_trigger_unknown_clip(song, run, named_track):
    drums = named_track('Drums')
    song.create_scene(-1)
    result = run('performance', 'trigger_clip', target={'role': 'drums'}, clip_name='Nope')
    assert result['status'] == 'error'
    assert not drums.clip_slots[0].is_playing
