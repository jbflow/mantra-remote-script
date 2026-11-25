"""Parameter actions against the Live mock. Values are display values, exactly as the UI shows them."""
import pytest

Live = pytest.importorskip("Live")


@pytest.fixture
def eq_frequency(named_track, add_parameter, shown_in_units):
    """A 'Pad' track with an EQ Eight whose Frequency is shown as 1000 Hz."""
    pad = named_track('Pad')
    eq = pad.insert_device('EQ Eight')
    return pad, add_parameter(eq, 'Frequency', 20.0, 22050.0, 1000.0)


def target(**extra):
    return dict({'track_name': 'Pad', 'device_name': 'EQ Eight', 'parameter_name': 'Frequency'}, **extra)


def test_set_display_value_without_a_unit(eq_frequency, ok):
    _, frequency = eq_frequency
    result = ok('parameters', 'set', target=target(), display_value=440)
    assert frequency.display_value == 440.0
    assert result['details'] == {'display_value': 440.0}


def test_set_takes_amount_as_the_display_value(eq_frequency, ok):
    _, frequency = eq_frequency
    ok('parameters', 'set', target=target(), amount=2500, unit='hz')
    assert frequency.display_value == 2500.0


def test_increase_moves_the_display_value(eq_frequency, ok):
    _, frequency = eq_frequency
    result = ok('parameters', 'increase', target=target(), amount=200, unit='hz')
    assert frequency.display_value == 1200.0
    assert result['details'] == {'display_value': 1200.0}


def test_decrease_frequency_example(eq_frequency, ok):
    _, frequency = eq_frequency
    ok('parameters', 'decrease', target=target(), amount=200, unit='hz')
    assert frequency.display_value == 800.0


def test_increase_without_a_unit(eq_frequency, ok):
    _, frequency = eq_frequency
    ok('parameters', 'increase', target=target(), amount=50)
    assert frequency.display_value == 1050.0


def test_unit_must_match_how_the_parameter_is_shown(eq_frequency, run):
    _, frequency = eq_frequency
    result = run('parameters', 'set', target=target(), amount=-6, unit='db')
    assert result['status'] == 'error'
    assert 'parameter is not shown in db' in result['details']['message']
    assert frequency.display_value == 1000.0


def test_unknown_unit_is_rejected(eq_frequency, run):
    assert run('parameters', 'increase', target=target(), amount=1, unit='furlong')['status'] == 'error'


@pytest.mark.parametrize('amount', ['loud', True, None])
def test_non_numeric_amount_is_rejected(eq_frequency, run, amount):
    _, frequency = eq_frequency
    assert run('parameters', 'set', target=target(), amount=amount)['status'] == 'error'
    assert frequency.display_value == 1000.0


def test_missing_target_is_rejected(run):
    assert run('parameters', 'increase', amount=1)['status'] == 'error'


def test_unknown_parameter_is_reported_by_name(eq_frequency, run):
    result = run('parameters', 'set', target=target(parameter_name='Resonance'), amount=1)
    assert result['status'] == 'error'
    assert 'parameter not found: resonance' in result['details']['message']


def test_parameter_by_index_and_device_by_index(eq_frequency, ok):
    _, frequency = eq_frequency
    ok('parameters', 'set', target={'track_name': 'Pad', 'device_index': 0, 'parameter_index': 1}, amount=600)
    assert frequency.display_value == 600.0


def test_track_index_out_of_range_is_an_error(eq_frequency, run):
    result = run('parameters', 'set', target={'index': 5, 'device_name': 'EQ Eight', 'parameter_name': 'Frequency'},
                 amount=1)
    assert result['status'] == 'error'


def test_mixer_volume_is_the_default_when_no_device_is_named(named_track, shown_in_units, ok):
    lead = named_track('Lead Vocal')
    ok('parameters', 'set', target={'track_name': 'Lead Vocal', 'parameter_name': 'Volume'}, amount=-6, unit='db')
    assert lead.mixer_device.volume.display_value == -6.0


def test_mixer_is_named_explicitly_too(named_track, shown_in_units, ok):
    lead = named_track('Lead Vocal')
    ok('parameters', 'increase', target={'track_name': 'Lead Vocal', 'device_name': 'Mixer',
                                         'parameter_name': 'Volume'}, amount=2, unit='db')
    assert lead.mixer_device.volume.display_value == 2.0


def test_mixer_parameter_index_out_of_range_is_an_error(named_track, run):
    named_track('Lead Vocal')
    result = run('parameters', 'set', target={'track_name': 'Lead Vocal', 'device_name': 'mixer',
                                              'parameter_index': 9}, amount=1)
    assert result['status'] == 'error'
