import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from .utils import *


class SceneActions(ControlSurfaceComponent):
    __module__ = __name__
    def __init__(self, c_instance, config):
        ControlSurfaceComponent.__init__(self, c_instance)
        self._c_instance = c_instance
        self.config = config
        self.rename = None
        self._verbs = {
            VERBS['rename']: self.rename_scene,
            VERBS['select']: self.select_scene,
            VERBS['delete']: self.delete_scene,
            VERBS['duplicate']: self.duplicate_scene,
            VERBS['load']: self.create_scene,
            VERBS['launch']: self.launch_scene,
        }
        self.scenes = list(self.song().scenes)
        self.song().add_scenes_listener(self.scenes_changed)
    def scenes_changed(self):
        self.scenes = list(self.song().scenes)

    def get_action(self, **kwargs):
        self.scenes_changed()
        index, action, quantity = convert_bytes(kwargs['noun_adj'][1:]) - 1, kwargs['verb'], kwargs['adverb']
        if action == 1:
            self.rename = ''.join([chr(c) for c in kwargs['adverb']])
        self.config.update_scenes()
        return 0 if index > len(self.scenes) else self._verbs[action](index, quantity)

    @undo_step
    def rename_scene(self, *bytes):
        self.scenes[bytes[0]].name = self.rename

    @undo_step
    def select_scene(self, *bytes):
        if self.song().view.selected_scene != self.scenes[bytes[0]]:
            self.song().view.selected_scene = self.scenes[bytes[0]]
            return 0
        return 1

    @undo_step
    def delete_scene(self, *bytes):
        self.song().delete_scene(bytes[0])
        return 1

    @undo_step
    def duplicate_scene(self, *bytes):
        self.song().duplicate_scene(bytes[0])
        return 1
    
    @undo_step
    def launch_scene(self, *bytes):
        self.scenes[bytes[0]].fire()
        return 1

    @undo_step
    def create_scene(self, *bytes):
        x = 0
        while x < bytes[1]:
            self.song().create_scene(-1)
            x += 1
