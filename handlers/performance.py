from .common import ActionError, Domain, find_clip_slot, find_scene, find_track


class PerformanceHandler(Domain):
    actions = ('trigger_scene', 'trigger_clip')

    def trigger_scene(self, payload, target, song, application):
        find_scene(song, _name_or_number(payload, 'scene_name')).fire()

    def trigger_clip(self, payload, target, song, application):
        track = find_track(song, target)
        find_clip_slot(track, _name_or_number(payload, 'clip_name')).fire()


def _name_or_number(payload, key):
    """Scenes and clips can be named or given by their 1-based position."""
    value = payload.get(key)
    if value is None or value == '':
        raise ActionError('missing or invalid field: %s' % key)
    return value
