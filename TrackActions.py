import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from .utils import *

class TrackActions(ControlSurfaceComponent):
    __module__ = __name__

    def __init__(self, c_instance):
        ControlSurfaceComponent.__init__(self, c_instance)
        self._c_instance = c_instance
        self.rename = None
        self._verbs = {
            VERBS['rename']: self.rename_track,
            VERBS['select']: self.select_track,
            VERBS['delete']: self.delete_track,
            VERBS['duplicate']: self.duplicate_track,
            VERBS['arm']: self.arm_track,
            VERBS['unarm']: self.unarm_track,
            VERBS['solo']: self.solo_track,
            VERBS['unsolo']: self.unsolo_track,
            VERBS['mute']: self.mute_track,
            VERBS['unmute']: self.unmute_track,
            VERBS['load']: self.load_track
        }
        self.tracks = list(self.song().tracks)
        self.song().add_tracks_listener(self.tracks_changed)

    def tracks_changed(self):
        self.tracks = list(self.song().tracks)

    def set_message(self, midi_bytes):
        self.midi_message = midi_bytes

    def get_action(self, **kwargs):
        self.tracks_changed()
        full_message, index, action = kwargs['full_message'], convert_bytes(kwargs['noun_adj'][1:]) - 1, kwargs['verb']
        if action == 1: 
            self.rename = ''.join([chr(c) for c in kwargs['adverb']])  
        return self._verbs[action](index)

    @undo_step
    def rename_track(self, *bytes):
        self.tracks[bytes[0]].name = self.rename
        return 1

    @undo_step
    def select_track(self, *bytes):
        if self.song().view.selected_track != self.tracks[bytes[0]]:
            self.song().view.selected_track = self.tracks[bytes[0]]
            return 1
        return 0

    @undo_step
    def delete_track(self, *bytes):
        self.song().delete_track(bytes[0])
        return 1

    @undo_step
    def duplicate_track(self, *bytes):
        self.song().duplicate_track(bytes[0])
        return 1

    @undo_step
    def arm_track(self, *bytes):
        if self.tracks[bytes[0]].arm == 0:
            self.tracks[bytes[0]].arm = 1
            return 1
        return 2

    @undo_step
    def unarm_track(self, *bytes):
        if self.tracks[bytes[0]].arm == 1:
            self.tracks[bytes[0]].arm = 0
            return 1
        return 2

    @undo_step
    def solo_track(self, *bytes):
        if self.tracks[bytes[0]].solo == 0:
            self.tracks[bytes[0]].solo = 1
            return 1
        return 2

    @undo_step
    def unsolo_track(self, *bytes):
        if self.tracks[bytes[0]].solo == 1:
            self.tracks[bytes[0]].solo = 0
            return 1
        return 2

    @undo_step
    def mute_track(self, *bytes):
        if self.tracks[bytes[0]].mute == 0:
            self.tracks[bytes[0]].mute = 1
            return 1
        return 2

    @undo_step
    def unmute_track(self, *bytes):
        if self.tracks[bytes[0]].mute == 1:
            self.tracks[bytes[0]].mute = 0
            return 1
        return 2

    @undo_step
    def load_track(self, *bytes):
        self.type_map = {
            16126: self.song().create_audio_track,
            16382: self.song().create_midi_track,
            16254: self.song().create_return_track
        }
        self.type_map[bytes[0]]()
        return 1