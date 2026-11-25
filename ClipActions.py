import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from .utils import *


class ClipActions(ControlSurfaceComponent):
    __module__ = __name__
    def __init__(self, c_instance):
        ControlSurfaceComponent.__init__(self, c_instance)
        self._c_instance = c_instance
        self.rename = None
        self._verbs = {
            VERBS['rename']: self.rename_clip,
            VERBS['select']: self.select_clip,
            VERBS['delete']: self.delete_clip,
            VERBS['duplicate']: self.duplicate_clip,
            VERBS['launch']: self.launch_clip_slot
        }
        self.tracks = self.song().tracks
        self.track = None
        self.clip_slots = None

    def get_action(self, **kwargs):
        self.tracks = self.song().tracks
        index, track, action, quantity = convert_bytes(kwargs['noun_adj'][4:]) - 1, convert_bytes(kwargs['noun_adj'][1:3]) - 1, \
                               kwargs['verb'], kwargs['adverb']
        if action == 1:
            self.rename = ''.join([chr(c) for c in kwargs['adverb']])
        if track > len(self.tracks):
            return 1
        self.track = self.tracks[track]
        if self.song().view.selected_track != self.track:
            self.song().view.selected_track = self.track
        self.clip_slots = self.track.clip_slots
        return (
            2
            if index > len(self.clip_slots)
            else self._verbs[action](index, quantity)
        )
        
    @undo_step
    def rename_clip(self, *bytes):
        if self.track.clip_slots[bytes[0]].has_clip:
            self.track.clip_slots[bytes[0]].clip.name = self.rename
            return 1
        return 0

    @undo_step
    def select_clip(self, *bytes):
        if self.song().view.selected_scene != self.song().scenes[bytes[0]] and self.track.clip_slots[bytes[0]].has_clip:
            self.song().view.selected_scene = self.song().scenes[bytes[0]]
            return 1
        return 0

    @undo_step
    def delete_clip(self, *bytes):
        self.track.delete_clip(list(self.track.clip_slots)[bytes[0]].clip)
        return 1

    @undo_step
    def duplicate_clip(self, *bytes):
        if self.track.clip_slots[bytes[0]].has_clip and not self.track.clip_slots[bytes[0] + 1].has_clip:
            self.track.clip_slots[bytes[0]].duplicate_clip_to(self.track.clip_slots[bytes[0] + 1])
            return 1
        return 0

    @undo_step
    def create_clip(self, *bytes):
        if self.track.has_midi_input and not self.track.clip_slots[bytes[0]].has_clip:
            self.track.clip_slots[bytes[0]].create_clip(4)
            return 1
        return 0
    
    @undo_step
    def launch_clip_slot(self, *bytes):
        self.track.clip_slots[bytes[0] - 1].fire()
        return 0
