from collections import namedtuple

try:
    from .Logging import logger
    from .Targets import (ActionError, find_browser_item, find_clip_slot, find_scene, find_track,
                          locate_track)
except ImportError:
    import logging
    from Targets import (ActionError, find_browser_item, find_clip_slot, find_scene, find_track,
                         locate_track)
    logger = logging.getLogger("mantra")

# song and application are callables so the handlers never depend on a ControlSurface.
Context = namedtuple('Context', 'song application')

TEMPO_RANGE = (20.0, 999.0)
DENOMINATORS = (1, 2, 4, 8, 16)
# Roles that have no Live track to create.
UNCREATABLE_ROLES = ('master', 'group')


# ---------------------------------------------------------------- argument checks

def _number(intent, key, low=None, high=None):
    value = intent.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActionError('missing or invalid field: %s' % key)
    if (low is not None and value < low) or (high is not None and value > high):
        raise ActionError('%s out of range: %s' % (key, value))
    return value


def _text(intent, key):
    value = intent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ActionError('missing or invalid field: %s' % key)
    return value.strip()


def _beats_per_bar(song):
    return song.signature_numerator * 4.0 / song.signature_denominator


def _timecode_seconds(timecode):
    try:
        parts = [float(part) for part in timecode.strip().split(':')]
    except ValueError:
        parts = []
    if not 1 <= len(parts) <= 3 or any(part < 0 for part in parts):
        raise ActionError('invalid timecode: %s' % timecode)
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds


# ---------------------------------------------------------------- transport

def play(ctx, intent):
    song = ctx.song()
    if not song.is_playing:
        song.start_playing()


def stop(ctx, intent):
    song = ctx.song()
    if song.is_playing:
        song.stop_playing()


def record(ctx, intent):
    ctx.song().record_mode = True


def toggle_record(ctx, intent):
    song = ctx.song()
    song.record_mode = not song.record_mode


def locate(ctx, intent):
    """bars and beats are 1-based; a timecode assumes the current tempo holds from the start."""
    song = ctx.song()
    if 'timecode' in intent:
        seconds = _timecode_seconds(_text(intent, 'timecode'))
        song.current_song_time = seconds * song.tempo / 60.0
        return
    bars = _number(intent, 'bars', low=1)
    beats = _number(intent, 'beats', low=1) if 'beats' in intent else 1
    beat_length = 4.0 / song.signature_denominator
    song.current_song_time = (bars - 1) * _beats_per_bar(song) + (beats - 1) * beat_length


def set_tempo(ctx, intent):
    ctx.song().tempo = float(_number(intent, 'bpm', *TEMPO_RANGE))


def set_time_signature(ctx, intent):
    numerator = _number(intent, 'numerator', 1, 99)
    denominator = _number(intent, 'denominator')
    if int(numerator) != numerator or denominator not in DENOMINATORS:
        raise ActionError('unsupported time signature: %s/%s' % (numerator, denominator))
    song = ctx.song()
    song.signature_numerator = int(numerator)
    song.signature_denominator = int(denominator)


def metronome_on(ctx, intent):
    ctx.song().metronome = True


def metronome_off(ctx, intent):
    ctx.song().metronome = False


def loop_on(ctx, intent):
    ctx.song().loop = True


def loop_off(ctx, intent):
    ctx.song().loop = False


def set_loop(ctx, intent):
    """startBars is 1-based; turns the loop on."""
    song = ctx.song()
    start = _number(intent, 'startBars', low=1)
    length = _number(intent, 'lengthBars')
    if length <= 0:
        raise ActionError('lengthBars out of range: %s' % length)
    bar = _beats_per_bar(song)
    song.loop_start = (start - 1) * bar
    song.loop_length = length * bar
    song.loop = True


# ---------------------------------------------------------------- structure

def create_track(ctx, intent):
    role = _text(intent, 'role')
    kind = intent.get('type') or 'audio'
    if kind not in ('audio', 'midi'):
        raise ActionError('invalid track type: %s' % kind)
    if role.lower() in UNCREATABLE_ROLES:
        raise ActionError('cannot create a track for role: %s' % role)
    song = ctx.song()
    create = song.create_midi_track if kind == 'midi' else song.create_audio_track
    track = create()
    if track is None:
        track = song.tracks[len(song.tracks) - 1]
    track.name = role.replace('_', ' ').title()
    return {'track_name': track.name}


def rename_track(ctx, intent):
    name = _text(intent, 'name')
    find_track(ctx.song(), intent.get('target')).name = name


def duplicate_track(ctx, intent):
    song = ctx.song()
    name = _text(intent, 'name') if intent.get('name') is not None else None
    kind, index = locate_track(song, find_track(song, intent.get('target')))
    if kind != 'track':
        raise ActionError('only regular tracks can be duplicated')
    song.duplicate_track(index)
    if name:
        song.tracks[index + 1].name = name


def remove_track(ctx, intent):
    song = ctx.song()
    kind, index = locate_track(song, find_track(song, intent.get('target')))
    if kind == 'track':
        song.delete_track(index)
    elif kind == 'return':
        song.delete_return_track(index)
    else:
        raise ActionError('the master track cannot be removed')


def select_track(ctx, intent):
    song = ctx.song()
    track = find_track(song, intent.get('target'))
    if song.view.selected_track != track:
        song.view.selected_track = track


def _set_track_flag(attribute, value):
    def handler(ctx, intent):
        track = find_track(ctx.song(), intent.get('target'))
        if attribute == 'arm' and not getattr(track, 'can_be_armed', True):
            raise ActionError('track cannot be armed: %s' % track.name)
        setattr(track, attribute, value)
    return handler


def load_device(ctx, intent):
    song = ctx.song()
    device = _text(intent, 'device')
    kind = intent.get('kind')
    if kind not in ('instrument', 'effect'):
        raise ActionError('missing or invalid field: kind')
    track = find_track(song, intent.get('target'))
    browser = ctx.application().browser
    item = find_browser_item(browser, device, kind)
    if song.view.selected_track != track:
        song.view.selected_track = track
    browser.load_item(item)
    return {'device': item.name}


# ---------------------------------------------------------------- performance

def trigger_scene(ctx, intent):
    scene_name = intent.get('scene_name')
    if scene_name is None or scene_name == '':
        raise ActionError('missing or invalid field: scene_name')
    find_scene(ctx.song(), scene_name).fire()


def trigger_clip(ctx, intent):
    clip_name = intent.get('clip_name')
    if clip_name is None or clip_name == '':
        raise ActionError('missing or invalid field: clip_name')
    track = find_track(ctx.song(), intent.get('target'))
    find_clip_slot(track, clip_name).fire()


# ---------------------------------------------------------------- dispatch

HANDLERS = {
    'transport': {
        'play': play,
        'stop': stop,
        'record': record,
        'toggle_record': toggle_record,
        'locate': locate,
        'set_tempo': set_tempo,
        'set_time_signature': set_time_signature,
        'metronome_on': metronome_on,
        'metronome_off': metronome_off,
        'loop_on': loop_on,
        'loop_off': loop_off,
        'set_loop': set_loop,
    },
    'structure': {
        'create_track': create_track,
        'rename_track': rename_track,
        'duplicate_track': duplicate_track,
        'remove_track': remove_track,
        'select_track': select_track,
        'arm_track': _set_track_flag('arm', True),
        'disarm_track': _set_track_flag('arm', False),
        'mute': _set_track_flag('mute', True),
        'unmute': _set_track_flag('mute', False),
        'solo': _set_track_flag('solo', True),
        'unsolo': _set_track_flag('solo', False),
        'load_device': load_device,
    },
    'performance': {
        'trigger_scene': trigger_scene,
        'trigger_clip': trigger_clip,
    },
}


def _error(envelope_id, message):
    return {'id': envelope_id, 'status': 'error', 'details': {'message': message}}


class Interpreter:
    """Runs MIP envelopes against Live. Everything Live-specific comes in through the two callables."""

    def __init__(self, get_song, get_application):
        self._context = Context(get_song, get_application)

    def execute_batch(self, envelopes):
        song = self._context.song()
        song.begin_undo_step()
        try:
            return [self._execute(envelope) for envelope in envelopes]
        finally:
            song.end_undo_step()

    def _execute(self, envelope):
        envelope_id = envelope.get('id')
        domain, intent = envelope.get('domain'), envelope.get('intent')
        action = intent.get('action') if isinstance(intent, dict) else None
        if not isinstance(domain, str) or not isinstance(action, str):
            return _error(envelope_id, 'invalid envelope: expected domain and intent.action')
        handler = HANDLERS.get(domain, {}).get(action)
        if handler is None:
            return _error(envelope_id, 'unsupported action: %s.%s' % (domain, action))
        try:
            details = handler(self._context, intent)
        except ActionError as e:
            return _error(envelope_id, str(e))
        except Exception as e:
            logger.error('%s.%s failed: %s' % (domain, action, e))
            return _error(envelope_id, str(e))
        result = {'id': envelope_id, 'status': 'ok'}
        if details:
            result['details'] = details
        return result
