import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from .utils import *
from .constants import *


class GlobalActions(ControlSurfaceComponent):
    __module__ = __name__

    def __init__(self, c_instance, config):
        ControlSurfaceComponent.__init__(self, c_instance)
        self._c_instance = c_instance
        self._config = config
        self._verbs = {
            VERBS['undo']: self._undo,
            VERBS['redo']: self._redo
        }

    def get_action(self, **kwargs):  
        action = kwargs['verb']
        return self._verbs[action]()

    def _undo(self):

        if self.song().can_undo:
            self.song().undo()
            return 1
        
    def _redo(self):
        try:
            if self.song().can_redo:
                self.song().redo()
                return 1
        except Exception as e:
            pass