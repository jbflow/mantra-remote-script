"""Structure actions against the Live mock: tracks, track flags, browser loading, devices, and target resolution."""
import pytest

Live = pytest.importorskip("Live")


def calls(name):
    return [r for r in Live.call_log if r.name == name]


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


def test_rename_track(song, ok, named_track):
    track = named_track('Drums')
    ok('structure', 'rename_track', target={'track_name': 'drums'}, name='Beats')
    assert track.name == 'Beats'


def test_duplicate_track_by_role_with_name(song, ok, named_track):
    named_track('Drums')
    bass = named_track('Bass')
    ok('structure', 'duplicate_track', target={'role': 'bass'}, name='Bass Double')
    assert [t.name for t in song.tracks] == ['Drums', 'Bass', 'Bass Double']
    assert calls('duplicate_track')[0].args == (1,)
    assert song.tracks[1] == bass


def test_duplicate_track_keeps_name_when_none_given(song, ok, named_track):
    named_track('Bass')
    ok('structure', 'duplicate_track', target={'role': 'bass'})
    assert [t.name for t in song.tracks] == ['Bass', 'Bass']


def test_remove_track(song, ok, named_track):
    named_track('Keep')
    named_track('Scratch Pad')
    ok('structure', 'remove_track', target={'track_name': 'Scratch Pad'})
    assert [t.name for t in song.tracks] == ['Keep']
    assert calls('delete_track')[0].args == (1,)


def test_remove_return_track(song, ok, named_track):
    named_track('Keep')
    song.create_return_track()
    ok('structure', 'remove_track', target={'track_name': 'A-Return'})
    assert len(song.return_tracks) == 0 and len(song.tracks) == 1


def test_remove_master_is_refused(song, run):
    assert run('structure', 'remove_track', target={'role': 'master'})['status'] == 'error'


def test_select_track(song, ok, named_track):
    named_track('One')
    two = named_track('Two')
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
def test_track_flags(song, ok, named_track, action, attribute, value, start):
    named_track('Other')
    track = named_track('Lead')
    setattr(track, attribute, start)
    ok('structure', action, target={'track_name': 'Lead'})
    assert bool(getattr(track, attribute)) is value
    assert not getattr(song.tracks[0], attribute)


def test_arm_master_is_refused(song, run):
    assert run('structure', 'arm_track', target={'role': 'master'})['status'] == 'error'


def test_load_instrument(song, ok, named_track):
    named_track('Keys')
    pad = named_track('Pad')
    song.view.selected_track = song.tracks[0]
    result = ok('structure', 'load_device', target={'track_name': 'Pad'}, device='operator', kind='instrument')
    assert [d.name for d in pad.devices] == ['Operator']
    assert song.view.selected_track == pad
    assert result['details'] == {'device': 'Operator'}


def test_load_effect_with_fuzzy_name(song, ok, named_track):
    track = named_track('Pad')
    ok('structure', 'load_device', target={'track_name': 'Pad'}, device='reverbb', kind='effect')
    assert [d.name for d in track.devices] == ['Reverb']


def test_load_device_not_found(song, run, named_track):
    track = named_track('Pad')
    result = run('structure', 'load_device', target={'track_name': 'Pad'}, device='Zzzzzzzz Qqqq', kind='effect')
    assert result['status'] == 'error' and 'not found' in result['details']['message']
    assert not list(track.devices)
    assert not calls('load_item')


def test_select_device_by_name_selects_track_and_device(song, ok, named_track):
    keys = named_track('Keys')
    keys.insert_device('EQ Eight')
    keys.insert_device('Operator')
    ok('structure', 'select_device', target={'track_name': 'Keys'}, device_name='operator')
    assert song.view.selected_track == keys
    # The mock only logs View.select_device; it does not move the selection.
    assert [r.args[0] for r in calls('select_device')] == [keys.devices[1]]


def test_rename_device_by_index(song, ok, named_track):
    keys = named_track('Keys')
    keys.insert_device('EQ Eight')
    keys.insert_device('Operator')
    ok('structure', 'rename_device', target={'track_name': 'Keys'}, device_index=1, name='Pad')
    assert [d.name for d in keys.devices] == ['EQ Eight', 'Pad']


def test_delete_device_by_name(song, ok, named_track):
    keys = named_track('Keys')
    keys.insert_device('EQ Eight')
    keys.insert_device('Operator')
    ok('structure', 'delete_device', target={'track_name': 'Keys'}, device_name='Operator')
    assert [d.name for d in keys.devices] == ['EQ Eight']


def test_device_index_out_of_range_is_an_error(song, run, named_track):
    keys = named_track('Keys')
    keys.insert_device('EQ Eight')
    result = run('structure', 'delete_device', target={'track_name': 'Keys'}, device_index=4)
    assert result['status'] == 'error'
    assert [d.name for d in keys.devices] == ['EQ Eight']


# ------------------------------------------------------------------ target resolution

def test_target_by_one_based_index(song, ok, named_track):
    named_track('A')
    b = named_track('B')
    ok('structure', 'rename_track', target={'track_name': 2}, name='Second')
    assert b.name == 'Second'


def test_target_name_wins_over_index(song, ok, named_track):
    named_track('Filler')
    named_track('1')
    ok('structure', 'rename_track', target={'track_name': '1'}, name='Named One')
    assert [t.name for t in song.tracks] == ['Filler', 'Named One']


def test_target_by_role_substring_with_underscore(song, ok, named_track):
    named_track('Drums')
    vocal = named_track('Lead Vocal 1')
    ok('structure', 'rename_track', target={'role': 'lead_vocal'}, name='Vox')
    assert vocal.name == 'Vox'


def test_target_by_role_category_and_detail(song, ok, named_track):
    named_track('Drums')
    synth = named_track('Warm Synth')
    ok('structure', 'rename_track', target={'role_category': 'rhythm', 'role_detail': 'synth'}, name='Warm')
    assert synth.name == 'Warm'


def test_target_master(song, ok, named_track):
    named_track('Drums')
    ok('structure', 'rename_track', target={'role': 'master'}, name='Main')
    assert song.master_track.name == 'Main'


def test_target_falls_back_to_selected_track_when_empty(song, ok, named_track):
    named_track('One')
    two = named_track('Two')
    song.view.selected_track = two
    ok('structure', 'rename_track', target={}, name='Chosen')
    ok('structure', 'mute')
    assert two.name == 'Chosen' and two.mute


def test_unresolved_target_is_an_error_not_the_selected_track(song, run, named_track):
    named_track('Drums')
    result = run('structure', 'remove_track', target={'track_name': 'Scratch Pad'})
    assert result['status'] == 'error' and 'not found' in result['details']['message']
    assert [t.name for t in song.tracks] == ['Drums']
    assert not calls('delete_track')
