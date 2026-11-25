from .common import ActionError, Domain, number, text

TEMPO_RANGE = (20.0, 999.0)
DENOMINATORS = (1, 2, 4, 8, 16)


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


class TransportHandler(Domain):
    actions = ('play', 'stop', 'record', 'toggle_record', 'locate', 'set_tempo', 'set_time_signature',
               'metronome_on', 'metronome_off', 'loop_on', 'loop_off', 'set_loop', 'undo', 'redo')

    def play(self, payload, target, song, application):
        if not song.is_playing:
            song.start_playing()

    def stop(self, payload, target, song, application):
        if song.is_playing:
            song.stop_playing()

    def record(self, payload, target, song, application):
        song.record_mode = True

    def toggle_record(self, payload, target, song, application):
        song.record_mode = not song.record_mode

    def locate(self, payload, target, song, application):
        """bars and beats are 1-based; a timecode assumes the current tempo holds from the start."""
        if 'timecode' in payload:
            seconds = _timecode_seconds(text(payload, 'timecode'))
            song.current_song_time = seconds * song.tempo / 60.0
            return
        bars = number(payload, 'bars', low=1)
        beats = number(payload, 'beats', low=1) if 'beats' in payload else 1
        beat_length = 4.0 / song.signature_denominator
        song.current_song_time = (bars - 1) * _beats_per_bar(song) + (beats - 1) * beat_length

    def set_tempo(self, payload, target, song, application):
        song.tempo = float(number(payload, 'bpm', *TEMPO_RANGE))

    def set_time_signature(self, payload, target, song, application):
        numerator = number(payload, 'numerator', 1, 99)
        denominator = number(payload, 'denominator')
        if int(numerator) != numerator or denominator not in DENOMINATORS:
            raise ActionError('unsupported time signature: %s/%s' % (numerator, denominator))
        song.signature_numerator = int(numerator)
        song.signature_denominator = int(denominator)

    def metronome_on(self, payload, target, song, application):
        song.metronome = True

    def metronome_off(self, payload, target, song, application):
        song.metronome = False

    def loop_on(self, payload, target, song, application):
        song.loop = True

    def loop_off(self, payload, target, song, application):
        song.loop = False

    def set_loop(self, payload, target, song, application):
        """startBars is 1-based; turns the loop on."""
        start = number(payload, 'startBars', low=1)
        length = number(payload, 'lengthBars')
        if length <= 0:
            raise ActionError('lengthBars out of range: %s' % length)
        bar = _beats_per_bar(song)
        song.loop_start = (start - 1) * bar
        song.loop_length = length * bar
        song.loop = True

    def undo(self, payload, target, song, application):
        if song.can_undo:
            song.undo()

    def redo(self, payload, target, song, application):
        if song.can_redo:
            song.redo()
