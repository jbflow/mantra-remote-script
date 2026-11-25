try:
    from ..Targets import (ActionError, find_browser_item, find_clip_slot, find_scene, find_track,
                           locate_track)
except (ImportError, ValueError):
    from Targets import (ActionError, find_browser_item, find_clip_slot, find_scene, find_track,
                         locate_track)


class Domain(object):
    """One MIP domain. Subclasses list their actions and implement a method for each."""
    actions = ()

    def supports(self, action):
        return action in self.actions

    def handle(self, action, payload, target, song, application):
        """Runs one action against Live and returns (status, details). Raises ActionError on bad input."""
        if not self.supports(action):
            raise ActionError('unsupported action: %s' % action)
        return 'ok', getattr(self, action)(payload, target, song, application)


# ---------------------------------------------------------------- argument checks

def number(payload, key, low=None, high=None):
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActionError('missing or invalid field: %s' % key)
    if (low is not None and value < low) or (high is not None and value > high):
        raise ActionError('%s out of range: %s' % (key, value))
    return value


def text(payload, key):
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ActionError('missing or invalid field: %s' % key)
    return value.strip()


def pick(items, payload, index_key, name_key, label):
    """Picks an item by 0-based index_key, or by case-insensitive name under name_key."""
    if index_key in payload:
        index = number(payload, index_key, low=0)
        if int(index) != index or index >= len(items):
            raise ActionError('%s index out of range: %s' % (label, index))
        return items[int(index)]
    name = text(payload, name_key).lower()
    for item in items:
        if item.name.lower() == name:
            return item
    raise ActionError('%s not found: %s' % (label, name))


# ---------------------------------------------------------------- target helpers

def find_device(track, payload):
    return pick(track.devices, payload, 'device_index', 'device_name', 'device')


def focus_track(song, track):
    if song.view.selected_track != track:
        song.view.selected_track = track
