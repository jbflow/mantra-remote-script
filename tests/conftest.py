import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Units the mock's parameters are shown in, by parameter name. The mock has no display strings of its own.
UNIT_FOR_PARAMETER = {'Frequency': 'Hz', 'Attack': 'ms', 'Volume': 'dB'}


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


@pytest.fixture
def song(mock_live_session):
    return mock_live_session


@pytest.fixture
def named_track(song):
    """named_track(name, midi=True) -> a new track with that name."""
    def _named_track(name, midi=True):
        track = song.create_midi_track() if midi else song.create_audio_track()
        track.name = name
        return track
    return _named_track


@pytest.fixture
def run(song):
    """run(domain, action, **fields) -> the result of one envelope, run as its own batch."""
    import Live
    from handlers import execute_batch
    app = Live.Application.get_application()

    def _run(domain, action, **fields):
        envelope = {'id': 'e1', 'domain': domain, 'intent': dict(fields, action=action)}
        results = execute_batch([envelope], song, app)
        assert len(results) == 1 and results[0]['id'] == 'e1'
        return results[0]
    return _run


@pytest.fixture
def ok(run):
    """Like run, but asserts the action succeeded."""
    def _ok(domain, action, **fields):
        result = run(domain, action, **fields)
        assert result['status'] == 'ok', result
        return result
    return _ok


@pytest.fixture
def add_parameter(song):
    """add_parameter(device, name, low, high, display_value) -> a parameter on the device, showing display_value."""
    import Live

    def _add_parameter(device, name, low, high, display_value):
        param = Live.DeviceParameter.DeviceParameter(
            name=name, original_name=name, min=low, max=high, value=display_value,
            default_value=display_value, is_quantized=False, is_enabled=True)
        device._update('parameters', Live.Device.ATimeableValueVector(list(device.parameters) + [param]))
        param.display_value = display_value
        return param
    return _add_parameter


@pytest.fixture
def shown_in_units(monkeypatch):
    """Show each mock parameter in the unit its name implies, e.g. Frequency in Hz."""
    import Live

    def str_for_value(self, value):
        return '%.2f %s' % (value, UNIT_FOR_PARAMETER.get(self.name, ''))
    monkeypatch.setattr(Live.DeviceParameter.DeviceParameter, 'str_for_value', str_for_value)
