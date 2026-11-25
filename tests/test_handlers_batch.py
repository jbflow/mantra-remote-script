"""Batch behaviour shared by every domain: undo grouping, error results, envelope checks, and the registry."""
import json

import pytest

Live = pytest.importorskip("Live")

from handlers import REGISTRY, execute_batch  # noqa: E402
from Protocol import Protocol  # noqa: E402


@pytest.fixture
def app():
    return Live.Application.get_application()


def undo_steps():
    return [r.name for r in Live.call_log if r.name.endswith('undo_step')]


def test_batch_is_one_undo_step(song, app, named_track):
    named_track('Drums')
    batch = [
        {'id': 'a', 'domain': 'transport', 'intent': {'action': 'set_tempo', 'bpm': 90}},
        {'id': 'b', 'domain': 'structure', 'intent': {'action': 'mute', 'target': {'role': 'drums'}}},
        {'id': 'c', 'domain': 'transport', 'intent': {'action': 'metronome_on'}},
    ]
    del Live.call_log[:]
    results = execute_batch(batch, song, app)
    assert [r['status'] for r in results] == ['ok', 'ok', 'ok']
    names = [r.name for r in Live.call_log]
    assert names.count('begin_undo_step') == 1 and names.count('end_undo_step') == 1
    assert names[0] == 'begin_undo_step' and names[-1] == 'end_undo_step'
    assert {'tempo', 'mute', 'metronome'} <= set(names[1:-1])


def test_failed_action_does_not_abort_the_batch_or_the_undo_step(song, app):
    batch = [
        {'id': 'a', 'domain': 'transport', 'intent': {'action': 'set_tempo', 'bpm': 'fast'}},
        {'id': 'b', 'domain': 'transport', 'intent': {'action': 'metronome_on'}},
    ]
    del Live.call_log[:]
    results = execute_batch(batch, song, app)
    assert [(r['id'], r['status']) for r in results] == [('a', 'error'), ('b', 'ok')]
    assert song.metronome
    assert undo_steps() == ['begin_undo_step', 'end_undo_step']


def test_undo_step_is_closed_when_the_batch_blows_up(song, app):
    def envelopes():
        yield {'id': 'a', 'domain': 'transport', 'intent': {'action': 'metronome_on'}}
        raise RuntimeError('boom')

    del Live.call_log[:]
    with pytest.raises(RuntimeError):
        execute_batch(envelopes(), song, app)
    assert undo_steps() == ['begin_undo_step', 'end_undo_step']


def test_handler_exception_becomes_an_error_result(song, app, monkeypatch):
    def boom():
        raise RuntimeError('live said no')
    monkeypatch.setattr(song, 'start_playing', boom)
    result = execute_batch([{'id': 'a', 'domain': 'transport', 'intent': {'action': 'play'}}], song, app)[0]
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
def test_malformed_envelope(song, app, envelope):
    result = execute_batch([envelope], song, app)[0]
    assert result['id'] == 'x' and result['status'] == 'error'
    assert result['details']['message'].startswith('invalid envelope')


def test_registry_lists_every_supported_action():
    assert {domain: sorted(handler.actions) for domain, handler in REGISTRY.items()} == {
        'transport': sorted([
            'play', 'stop', 'record', 'toggle_record', 'locate', 'set_tempo', 'set_time_signature',
            'metronome_on', 'metronome_off', 'loop_on', 'loop_off', 'set_loop', 'undo', 'redo']),
        'structure': sorted([
            'create_track', 'rename_track', 'duplicate_track', 'remove_track', 'select_track', 'arm_track',
            'disarm_track', 'mute', 'unmute', 'solo', 'unsolo', 'load_device',
            'select_device', 'rename_device', 'delete_device']),
        'performance': ['trigger_clip', 'trigger_scene'],
        'parameters': ['decrease', 'increase', 'set'],
    }


def test_through_the_protocol(song, app):
    class Batches:
        def execute_batch(self, envelopes):
            return execute_batch(envelopes, song, app)

    protocol = Protocol(Batches())
    message = json.dumps({'type': 'intent', 'payload': [
        {'domain': 'transport', 'intent': {'action': 'set_tempo', 'bpm': 140}},
        {'domain': 'music', 'intent': {'action': 'transpose', 'semitones': 2}},
    ]})
    kind, response = protocol.parse_message(message)
    assert kind == 'intent'
    assert [r['status'] for r in response['results']] == ['ok', 'error']
    assert [r['id'] for r in response['results']] == response['ack']['ids']
    assert song.tempo == 140.0
