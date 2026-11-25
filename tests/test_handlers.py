"""Handlers run against the Live mock: one test per MIP action, plus target resolution and undo grouping."""
import json

import pytest

Live = pytest.importorskip("Live")

from Handlers import Interpreter  # noqa: E402
from Protocol import Protocol  # noqa: E402


@pytest.fixture
def song(mock_live_session):
    return mock_live_session


@pytest.fixture
def interp(song):
    app = Live.Application.get_application()
    return Interpreter(lambda: song, lambda: app)


@pytest.fixture
def run(interp):
    """run('transport', 'play') -> the single result for that envelope."""
    def _run(domain, action, **fields):
        envelope = {'id': 'e1', 'domain': domain, 'intent': dict(fields, action=action)}
        results = interp.execute_batch([envelope])
        assert len(results) == 1 and results[0]['id'] == 'e1'
        return results[0]
    return _run


@pytest.fixture
def ok(run):
    def _ok(domain, action, **fields):
        result = run(domain, action, **fields)
        assert result['status'] == 'ok', result
        return result
    return _ok


def named_track(song, name, midi=True):
    track = song.create_midi_track() if midi else song.create_audio_track()
    track.name = name
    return track


def calls(name, target=None):
    return [r for r in Live.call_log if r.name == name and (target is None or r.target == target)]


# ------------------------------------------------------------------ transport

def test_play(song, ok):
    ok('transport', 'play')
    assert song.is_playing
    assert len(calls('start_playing')) == 1


def test_stop(song, ok):
    song.start_playing()
    ok('transport', 'stop')
    assert not song.is_playing


def test_record(song, ok):
    ok('transport', 'record')
    assert song.record_mode


def test_toggle_record(song, ok):
    ok('transport', 'toggle_record')
    assert song.record_mode
    ok('transport', 'toggle_record')
    assert not song.record_mode


def test_locate_bars_and_beats(song, ok):
    ok('transport', 'locate', bars=3)
    assert song.current_song_time == 8.0
    ok('transport', 'locate', bars=2, beats=3)
    assert song.current_song_time == 6.0


def test_locate_uses_the_time_signature(song, ok):
    song.signature_numerator, song.signature_denominator = 6, 8
    ok('transport', 'locate', bars=3)
    assert song.current_song_time == 6.0


def test_locate_timecode(song, ok):
    song.tempo = 120.0
    ok('transport', 'locate', timecode='0:01:30')
    assert song.current_song_time == 180.0


def test_locate_rejects_bad_input(run):
    assert run('transport', 'locate', bars=0)['status'] == 'error'
    assert run('transport', 'locate', timecode='soon')['status'] == 'error'
    assert run('transport', 'locate')['status'] == 'error'


def test_set_tempo(song, ok):
    ok('transport', 'set_tempo', bpm=128)
    assert song.tempo == 128.0


@pytest.mark.parametrize('bpm', [0, 19, 1000, '120', None])
def test_set_tempo_rejects_out_of_range(song, run, bpm):
    result = run('transport', 'set_tempo', bpm=bpm)
    assert result['status'] == 'error'
    assert song.tempo == 120.0


def test_set_time_signature(song, ok):
    ok('transport', 'set_time_signature', numerator=7, denominator=8)
    assert (song.signature_numerator, song.signature_denominator) == (7, 8)


def test_set_time_signature_rejects_bad_denominator(song, run):
    assert run('transport', 'set_time_signature', numerator=4, denominator=5)['status'] == 'error'
    assert (song.signature_numerator, song.signature_denominator) == (4, 4)


def test_metronome_on_off(song, ok):
    ok('transport', 'metronome_on')
    assert song.metronome
    ok('transport', 'metronome_off')
    assert not song.metronome


def test_loop_on_off(song, ok):
    ok('transport', 'loop_on')
    assert song.loop
    ok('transport', 'loop_off')
    assert not song.loop


def test_set_loop(song, ok):
    ok('transport', 'set_loop', startBars=3, lengthBars=2)
    assert (song.loop_start, song.loop_length, song.loop) == (8.0, 8.0, True)


# ------------------------------------------------------------------ structure

def test_create_audio_track_named_after_role(song, ok):
    result = ok('structure', 'create_track', role='drums', type='audio')
    track = song.tracks[0]
    assert track.name == 'Drums' and result['details'] == {'track_name': 'Drums'}
    assert track.has_audio_input and not track.has_midi_input


def test_create_midi_track(song, ok):
    ok('structure', 'create_track', role='lead_vocal', type='midi')
    assert song.tracks[0].name == 'Lead Vocal' and song.tracks[0].has_midi_input
    assert len(calls('create_midi_track')) == 1


def test_create_track_without_type_is_audio(song, ok):
    ok('structure', 'create_track', role='bass')
    assert song.tracks[0].has_audio_input


@pytest.mark.parametrize('role', ['master', 'group'])
def test_create_track_rejects_roles_without_a_live_track(song, run, role):
    assert run('structure', 'create_track', role=role)['status'] == 'error'
    assert len(song.tracks) == 0


def test_rename_track(song, ok):
    track = named_track(song, 'Drums')
    ok('structure', 'rename_track', target={'track_name': 'drums'}, name='Beats')
    assert track.name == 'Beats'


def test_duplicate_track_by_role_with_name(song, ok):
    named_track(song, 'Drums')
    bass = named_track(song, 'Bass')
    ok('structure', 'duplicate_track', target={'role': 'bass'}, name='Bass Double')
    assert [t.name for t in song.tracks] == ['Drums', 'Bass', 'Bass Double']
    assert calls('duplicate_track')[0].args == (1,)
    assert song.tracks[1] == bass


def test_duplicate_track_keeps_name_when_none_given(song, ok):
    named_track(song, 'Bass')
    ok('structure', 'duplicate_track', target={'role': 'bass'})
    assert [t.name for t in song.tracks] == ['Bass', 'Bass']


def test_remove_track(song, ok):
    named_track(song, 'Keep')
    named_track(song, 'Scratch Pad')
    ok('structure', 'remove_track', target={'track_name': 'Scratch Pad'})
    assert [t.name for t in song.tracks] == ['Keep']
    assert calls('delete_track')[0].args == (1,)


def test_remove_return_track(song, ok):
    named_track(song, 'Keep')
    song.create_return_track()
    ok('structure', 'remove_track', target={'track_name': 'A-Return'})
    assert len(song.return_tracks) == 0 and len(song.tracks) == 1


def test_remove_master_is_refused(song, run):
    assert run('structure', 'remove_track', target={'role': 'master'})['status'] == 'error'


def test_select_track(song, ok):
    named_track(song, 'One')
    two = named_track(song, 'Two')
    ok('structure', 'select_track', target={'track_name': 'Two'})
    assert song.view.selected_track == two


@pytest.mark.parametrize('action, attribute, value, start', [
    ('arm_track', 'arm', True, False),
    ('disarm_track', 'arm', False, True),
    ('mute', 'mute', True, False),
    ('unmute', 'mute', False, True),
    ('solo', 'solo', True, False),
    ('unsolo', 'solo', False, True),
])
def test_track_flags(song, ok, action, attribute, value, start):
    named_track(song, 'Other')
    track = named_track(song, 'Lead')
    setattr(track, attribute, start)
    ok('structure', action, target={'track_name': 'Lead'})
    assert bool(getattr(track, attribute)) is value
    assert not getattr(song.tracks[0], attribute)


def test_arm_master_is_refused(song, run):
    assert run('structure', 'arm_track', target={'role': 'master'})['status'] == 'error'


def test_load_instrument(song, ok):
    named_track(song, 'Keys')
    pad = named_track(song, 'Pad')
    song.view.selected_track = song.tracks[0]
    result = ok('structure', 'load_device', target={'track_name': 'Pad'}, device='operator', kind='instrument')
    assert [d.name for d in pad.devices] == ['Operator']
    assert song.view.selected_track == pad
    assert result['details'] == {'device': 'Operator'}


def test_load_effect_with_fuzzy_name(song, ok):
    track = named_track(song, 'Pad')
    ok('structure', 'load_device', target={'track_name': 'Pad'}, device='reverbb', kind='effect')
    assert [d.name for d in track.devices] == ['Reverb']


def test_load_device_not_found(song, run):
    track = named_track(song, 'Pad')
    result = run('structure', 'load_device', target={'track_name': 'Pad'}, device='Zzzzzzzz Qqqq', kind='effect')
    assert result['status'] == 'error' and 'not found' in result['details']['message']
    assert not list(track.devices)
    assert not calls('load_item')


# ------------------------------------------------------------------ target resolution

def test_target_by_one_based_index(song, ok):
    named_track(song, 'A')
    b = named_track(song, 'B')
    ok('structure', 'rename_track', target={'track_name': 2}, name='Second')
    assert b.name == 'Second'


def test_target_name_wins_over_index(song, ok):
    named_track(song, 'Filler')
    named_track(song, '1')
    ok('structure', 'rename_track', target={'track_name': '1'}, name='Named One')
    assert [t.name for t in song.tracks] == ['Filler', 'Named One']


def test_target_by_role_substring_with_underscore(song, ok):
    named_track(song, 'Drums')
    vocal = named_track(song, 'Lead Vocal 1')
    ok('structure', 'rename_track', target={'role': 'lead_vocal'}, name='Vox')
    assert vocal.name == 'Vox'


def test_target_by_role_category_and_detail(song, ok):
    named_track(song, 'Drums')
    synth = named_track(song, 'Warm Synth')
    ok('structure', 'rename_track', target={'role_category': 'rhythm', 'role_detail': 'synth'}, name='Warm')
    assert synth.name == 'Warm'


def test_target_master(song, ok):
    named_track(song, 'Drums')
    ok('structure', 'rename_track', target={'role': 'master'}, name='Main')
    assert song.master_track.name == 'Main'


def test_target_falls_back_to_selected_track_when_empty(song, ok):
    named_track(song, 'One')
    two = named_track(song, 'Two')
    song.view.selected_track = two
    ok('structure', 'rename_track', target={}, name='Chosen')
    ok('structure', 'mute')
    assert two.name == 'Chosen' and two.mute


def test_unresolved_target_is_an_error_not_the_selected_track(song, run):
    named_track(song, 'Drums')
    result = run('structure', 'remove_track', target={'track_name': 'Scratch Pad'})
    assert result['status'] == 'error' and 'not found' in result['details']['message']
    assert [t.name for t in song.tracks] == ['Drums']
    assert not calls('delete_track')


# ------------------------------------------------------------------ performance

def test_trigger_scene_by_name(song, ok):
    drums = named_track(song, 'Drums')
    verse, chorus = song.create_scene(-1), song.create_scene(-1)
    chorus.name = 'Chorus'
    drums.clip_slots[0].create_clip(4)
    drums.clip_slots[1].create_clip(4)
    ok('performance', 'trigger_scene', scene_name='chorus')
    assert len(calls('fire', 'Scene')) == 1
    assert drums.clip_slots[1].is_playing and not drums.clip_slots[0].is_playing


def test_trigger_scene_by_number(song, ok):
    named_track(song, 'Drums')
    first = song.create_scene(-1)
    song.create_scene(-1)
    first.clip_slots[0].create_clip(4)
    ok('performance', 'trigger_scene', scene_name=1)
    assert first.clip_slots[0].is_playing


def test_trigger_unknown_scene(song, run):
    song.create_scene(-1)
    assert run('performance', 'trigger_scene', scene_name='Nope')['status'] == 'error'
    assert not calls('fire')


def test_trigger_clip_by_name(song, ok):
    named_track(song, 'Other')
    drums = named_track(song, 'Drums')
    song.create_scene(-1)
    song.create_scene(-1)
    drums.clip_slots[1].create_clip(4)
    drums.clip_slots[1].clip.name = 'Fill'
    ok('performance', 'trigger_clip', target={'role': 'drums'}, clip_name='fill')
    assert drums.clip_slots[1].is_playing
    assert not drums.clip_slots[0].is_playing


def test_trigger_unknown_clip(song, run):
    drums = named_track(song, 'Drums')
    song.create_scene(-1)
    result = run('performance', 'trigger_clip', target={'role': 'drums'}, clip_name='Nope')
    assert result['status'] == 'error'
    assert not drums.clip_slots[0].is_playing


# ------------------------------------------------------------------ batch behaviour

def test_batch_is_one_undo_step(song, interp):
    named_track(song, 'Drums')
    batch = [
        {'id': 'a', 'domain': 'transport', 'intent': {'action': 'set_tempo', 'bpm': 90}},
        {'id': 'b', 'domain': 'structure', 'intent': {'action': 'mute', 'target': {'role': 'drums'}}},
        {'id': 'c', 'domain': 'transport', 'intent': {'action': 'metronome_on'}},
    ]
    del Live.call_log[:]
    results = interp.execute_batch(batch)
    assert [r['status'] for r in results] == ['ok', 'ok', 'ok']
    names = [r.name for r in Live.call_log]
    assert names.count('begin_undo_step') == 1 and names.count('end_undo_step') == 1
    assert names[0] == 'begin_undo_step' and names[-1] == 'end_undo_step'
    inside = names[1:-1]
    assert {'tempo', 'mute', 'metronome'} <= set(inside)


def test_failed_action_does_not_abort_the_batch_or_the_undo_step(song, interp):
    batch = [
        {'id': 'a', 'domain': 'transport', 'intent': {'action': 'set_tempo', 'bpm': 'fast'}},
        {'id': 'b', 'domain': 'transport', 'intent': {'action': 'metronome_on'}},
    ]
    del Live.call_log[:]
    results = interp.execute_batch(batch)
    assert [(r['id'], r['status']) for r in results] == [('a', 'error'), ('b', 'ok')]
    assert song.metronome
    assert [r.name for r in Live.call_log if r.name.endswith('undo_step')] == ['begin_undo_step', 'end_undo_step']


def test_undo_step_is_closed_when_the_batch_blows_up(interp):
    def envelopes():
        yield {'id': 'a', 'domain': 'transport', 'intent': {'action': 'metronome_on'}}
        raise RuntimeError('boom')

    del Live.call_log[:]
    with pytest.raises(RuntimeError):
        interp.execute_batch(envelopes())
    assert [r.name for r in Live.call_log if r.name.endswith('undo_step')] == ['begin_undo_step', 'end_undo_step']


def test_handler_exception_becomes_an_error_result(song, interp, monkeypatch):
    def boom():
        raise RuntimeError('live said no')
    monkeypatch.setattr(song, 'start_playing', boom)
    result = interp.execute_batch([{'id': 'a', 'domain': 'transport', 'intent': {'action': 'play'}}])[0]
    assert result == {'id': 'a', 'status': 'error', 'details': {'message': 'live said no'}}


@pytest.mark.parametrize('domain, action', [
    ('structure', 'bogus'),
    ('music', 'transpose'),
    ('nonsense', 'play'),
])
def test_unsupported_action(run, domain, action):
    result = run(domain, action)
    assert result == {'id': 'e1', 'status': 'error',
                      'details': {'message': 'unsupported action: %s.%s' % (domain, action)}}


@pytest.mark.parametrize('envelope', [
    {'id': 'x'},
    {'id': 'x', 'domain': 'transport'},
    {'id': 'x', 'domain': 'transport', 'intent': 'play'},
    {'id': 'x', 'domain': 'transport', 'intent': {}},
])
def test_malformed_envelope(interp, envelope):
    result = interp.execute_batch([envelope])[0]
    assert result['id'] == 'x' and result['status'] == 'error'
    assert result['details']['message'].startswith('invalid envelope')


def test_every_mip_action_in_the_three_domains_is_registered():
    from Handlers import HANDLERS
    assert {d: sorted(a) for d, a in HANDLERS.items()} == {
        'transport': sorted([
            'play', 'stop', 'record', 'toggle_record', 'locate', 'set_tempo', 'set_time_signature',
            'metronome_on', 'metronome_off', 'loop_on', 'loop_off', 'set_loop']),
        'structure': sorted([
            'create_track', 'rename_track', 'duplicate_track', 'remove_track', 'select_track', 'arm_track',
            'disarm_track', 'mute', 'unmute', 'solo', 'unsolo', 'load_device']),
        'performance': ['trigger_clip', 'trigger_scene'],
    }


def test_through_the_protocol(song, interp):
    protocol = Protocol(interp)
    message = json.dumps({'type': 'intent', 'payload': [
        {'domain': 'transport', 'intent': {'action': 'set_tempo', 'bpm': 140}},
        {'domain': 'music', 'intent': {'action': 'transpose', 'semitones': 2}},
    ]})
    kind, response = protocol.parse_message(message)
    assert kind == 'intent'
    assert [r['status'] for r in response['results']] == ['ok', 'error']
    assert [r['id'] for r in response['results']] == response['ack']['ids']
    assert song.tempo == 140.0
