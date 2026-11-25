import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from .utils import *



class CuePointActions(ControlSurfaceComponent):
    __module__ = __name__
    def __init__(self, c_instance):
        ControlSurfaceComponent.__init__(self, c_instance)
        self._c_instance = c_instance
        self.rename = None
        self._verbs = {
            VERBS['rename']: self.rename_cue_point,
            VERBS['select']: self.select_cue_point,
        }
    


    def get_action(self, **kwargs):
        cue_point, action = convert_bytes(kwargs['noun_adj'][1:]) - 1, kwargs['verb']
        return self._verbs[action](cue_point)

    @undo_step
    def rename_cue_point(self):
        pass
    
    @undo_step
    def select_cue_point(self, cue_point):
        self.song().cue_points[cue_point].jump()
        return 1
        
        
