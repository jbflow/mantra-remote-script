import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from .constants import *
from .utils import undo_step


class TransportActions(ControlSurfaceComponent):
    __module__ = __name__

    def __init__(self, c_instance):
        ControlSurfaceComponent.__init__(self, c_instance)
        self._c_instance = c_instance
        self.midi_message = None
        self._verbs = {
            VERBS['play']: self.play,
            VERBS['stop']: self.stop,
            VERBS['record']: self.record_enable,
            VERBS['loop']: self.loop_enable
        }

    def set_message(self, midi_bytes):
        self.midi_message = midi_bytes

    def get_action(self, **kwargs):
        action, value = kwargs['verb'], kwargs['adverb']
        return self._verbs[action]()

    @undo_step
    def play(self):
        if self.song().is_playing:
            return 0
        self.song().start_playing()
        return 1

    @undo_step
    def stop(self):
        if self.song().is_playing:
            self.song().stop_playing()
            return 1
        else:
            return 0

    @undo_step
    def record_enable(self):
        if self.song().record_mode != 0:
            return 0
        self.song().record_mode = 1
        return 1

    @undo_step
    def record_disable(self):
        if self.song().record_mode != 1:
            return 1
        self.song().record_mode = 0
        return 0

    @undo_step
    def overdub_enable(self):
        if self.song().arrangement_overdub != 0:
            return 0
        self.song().arrangement_overdub = 1
        return 1

    @undo_step
    def overdub_disable(self):
        if self.song().arrangement_overdub != 1:
            return 0
        self.song().arrangement_overdub = 0
        return 1

    @undo_step
    def loop_enable(self):
        if self.song().loop != 0:
            return 0
        self.song().loop = 1
        return 1

    @undo_step
    def loop_disable(self):
        if self.song().loop != 1:
            return 0
        self.song().loop = 0
        return 1

    @undo_step
    def click_enable(self):
        if self.song().metronome != 0:
            return 0
        self.song().metronome = 1
        return 1
    
    @undo_step
    def click_disable(self):
        if self.song().metronom != 1:
            return 0
        self.song().metronome = 0
        return 1

    @undo_step
    def set_tempo(self, value):
        if value > 999 or value <= 0:
            return 0
        if self.song().tempo != value:
            self.song().tempo = value
            return 1
        else:
            return 0


