from .common import (ActionError, Domain, find_browser_item, find_device, find_track, focus_track,
                     locate_track, text)

# Roles that have no Live track to create.
UNCREATABLE_ROLES = ('master', 'group')


def _device(song, target, payload):
    """Resolves a track and its device, and selects the track the way the device controls always did."""
    track = find_track(song, target)
    focus_track(song, track)
    return track, find_device(track, payload)


class StructureHandler(Domain):
    actions = ('create_track', 'rename_track', 'duplicate_track', 'remove_track', 'select_track',
               'arm_track', 'disarm_track', 'mute', 'unmute', 'solo', 'unsolo', 'load_device',
               'select_device', 'rename_device', 'delete_device')

    def create_track(self, payload, target, song, application):
        role = text(payload, 'role')
        kind = payload.get('type') or 'audio'
        if kind not in ('audio', 'midi'):
            raise ActionError('invalid track type: %s' % kind)
        if role.lower() in UNCREATABLE_ROLES:
            raise ActionError('cannot create a track for role: %s' % role)
        create = song.create_midi_track if kind == 'midi' else song.create_audio_track
        track = create()
        if track is None:
            track = song.tracks[len(song.tracks) - 1]
        track.name = role.replace('_', ' ').title()
        return {'track_name': track.name}

    def rename_track(self, payload, target, song, application):
        name = text(payload, 'name')
        find_track(song, target).name = name

    def duplicate_track(self, payload, target, song, application):
        name = text(payload, 'name') if payload.get('name') is not None else None
        kind, index = locate_track(song, find_track(song, target))
        if kind != 'track':
            raise ActionError('only regular tracks can be duplicated')
        song.duplicate_track(index)
        if name:
            song.tracks[index + 1].name = name

    def remove_track(self, payload, target, song, application):
        kind, index = locate_track(song, find_track(song, target))
        if kind == 'track':
            song.delete_track(index)
        elif kind == 'return':
            song.delete_return_track(index)
        else:
            raise ActionError('the master track cannot be removed')

    def select_track(self, payload, target, song, application):
        focus_track(song, find_track(song, target))

    def arm_track(self, payload, target, song, application):
        self._set_flag(payload, target, song, 'arm', True)

    def disarm_track(self, payload, target, song, application):
        self._set_flag(payload, target, song, 'arm', False)

    def mute(self, payload, target, song, application):
        self._set_flag(payload, target, song, 'mute', True)

    def unmute(self, payload, target, song, application):
        self._set_flag(payload, target, song, 'mute', False)

    def solo(self, payload, target, song, application):
        self._set_flag(payload, target, song, 'solo', True)

    def unsolo(self, payload, target, song, application):
        self._set_flag(payload, target, song, 'solo', False)

    def load_device(self, payload, target, song, application):
        device = text(payload, 'device')
        kind = payload.get('kind')
        if kind not in ('instrument', 'effect'):
            raise ActionError('missing or invalid field: kind')
        track = find_track(song, target)
        browser = application.browser
        item = find_browser_item(browser, device, kind)
        focus_track(song, track)
        browser.load_item(item)
        return {'device': item.name}

    def select_device(self, payload, target, song, application):
        track, device = _device(song, target, payload)
        if track.view.selected_device != device:
            song.view.select_device(device)

    def rename_device(self, payload, target, song, application):
        track, device = _device(song, target, payload)
        device.name = text(payload, 'name')

    def delete_device(self, payload, target, song, application):
        track, device = _device(song, target, payload)
        track.delete_device(list(track.devices).index(device))

    def _set_flag(self, payload, target, song, attribute, value):
        track = find_track(song, target)
        if attribute == 'arm' and not getattr(track, 'can_be_armed', True):
            raise ActionError('track cannot be armed: %s' % track.name)
        setattr(track, attribute, value)
