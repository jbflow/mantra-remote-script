import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from .utils import *


class DeviceActions(ControlSurfaceComponent):
    __module__ = __name__

    def __init__(self, c_instance):
        ControlSurfaceComponent.__init__(self, c_instance)
        self._c_instance = c_instance
        self.rename = None
        self._verbs = {
            1: self.rename_device,
            3: self.select_device,
            4: self.delete_device,
        }
        self.tracks = self.song().tracks
        self.track = None
        self.devices = None


    def get_action(self, **kwargs):
        self.tracks = self.song().tracks
        index, track, action = convert_bytes(kwargs['noun_adj'][4:]) - 1, convert_bytes(kwargs['noun_adj'][1:3]) - 1, kwargs['verb']
        if action == 1:
            self.rename = ''.join([chr(c) for c in kwargs['adverb']])
        if track > len(self.tracks):
            return 1
        self.track = self.tracks[track]
        if self.song().view.selected_track != self.track:
            self.song().view.selected_track = self.track
        self.devices = self.track.devices
        return 2 if index > len(self.devices) else self._verbs[action](index)

    @undo_step
    def rename_device(self, index):
        self.track.devices[index].name = self.rename

    @undo_step
    def select_device(self, index):
        if self.track.view.selected_device != self.devices[index]:
            self.song().view.select_device(self.devices[index])
            return 1
        return 0

    @undo_step
    def delete_device(self, index):
        self.track.delete_device(index)
        return 1
