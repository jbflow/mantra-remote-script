"""Transport actions against the Live mock."""
import pytest

Live = pytest.importorskip("Live")


def calls(name):
    return [r for r in Live.call_log if r.name == name]


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


def test_undo_and_redo(song, ok):
    ok('transport', 'set_tempo', bpm=140)
    ok('transport', 'undo')
    assert song.tempo == 120.0
    ok('transport', 'redo')
    assert song.tempo == 140.0


def test_undo_with_nothing_to_undo_is_a_no_op(song, ok):
    result = ok('transport', 'undo')
    assert result == {'id': 'e1', 'status': 'ok'}
    assert song.tempo == 120.0
