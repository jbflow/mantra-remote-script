from .common import ActionError, Domain, find_device, find_track, number, pick

# Units the MIP parameters domain allows. A unit is only a check: it must match the suffix of the parameter's display string.
UNITS = ('db', 'hz', 'ms', '%')
MIXER = 'mixer'


def _unit(payload):
    unit = payload.get('unit')
    if unit is None:
        return None
    if unit not in UNITS:
        raise ActionError('unsupported unit: %s' % unit)
    return unit


def _find_track(song, target):
    if 'index' in target:
        return pick(song.tracks, target, 'index', 'track_name', 'track')
    return find_track(song, target)


def _is_mixer(target):
    """The mixer is the default device: with no device named or indexed, the parameter is on the track's mixer."""
    if 'device_index' in target:
        return False
    name = target.get('device_name')
    return name is None or (isinstance(name, str) and name.strip().lower() == MIXER)


def _find_parameter(track, target):
    if _is_mixer(target):
        mixer = track.mixer_device
        parameters = [mixer.volume, mixer.panning] + list(mixer.sends)
    else:
        parameters = find_device(track, target).parameters
    return pick(parameters, target, 'parameter_index', 'parameter_name', 'parameter')


def _check_unit(param, unit):
    if not param.str_for_value(param.value).lower().endswith(unit):
        raise ActionError('parameter is not shown in %s: %s' % (unit, param.name))


class ParametersHandler(Domain):
    """Values are display values: exactly what the parameter shows in Live's UI, in its own units.

    increase/decrease move the display value by amount. set takes display_value (or amount) as the new value.
    unit is optional and only checks that the parameter is shown in that unit.
    """
    actions = ('increase', 'decrease', 'set')

    def increase(self, payload, target, song, application):
        return self._nudge(payload, target, song, 1)

    def decrease(self, payload, target, song, application):
        return self._nudge(payload, target, song, -1)

    def set(self, payload, target, song, application):
        param = self._resolve(payload, target, song)
        key = 'display_value' if 'display_value' in payload else 'amount'
        param.display_value = number(payload, key)
        return {'display_value': param.display_value}

    def _nudge(self, payload, target, song, direction):
        param = self._resolve(payload, target, song)
        param.display_value = param.display_value + direction * number(payload, 'amount')
        return {'display_value': param.display_value}

    def _resolve(self, payload, target, song):
        if not isinstance(target, dict):
            raise ActionError('missing or invalid field: target')
        param = _find_parameter(_find_track(song, target), target)
        unit = _unit(payload)
        if unit is not None:
            _check_unit(param, unit)
        return param
