from .constants import *
from .utils import *
import time


from _Framework.ControlSurfaceComponent import ControlSurfaceComponent

class BrowserActions(ControlSurfaceComponent):
    def __init__(self, c_instance, config):
        super(BrowserActions, self).__init__(c_instance)
        self._c_instance = c_instance
        self._config = config
        self.browser = self.application().browser
        self.verbs = {VERBS['load']: self.load_item
                      }
        self.browser_lists = {NOUNS['instrument']: self.browser.instruments,
                              NOUNS['audio_effect']: self.browser.audio_effects,
                              NOUNS['midi_effect']: self.browser.midi_effects,
                              NOUNS['browser_clip']: self.browser.clips,
                              NOUNS['favorites']: self.browser.colors[0],
        }

    def disconnect(self):
        ControlSurfaceComponent.disconnect(self)

    def get_action(self, **kwargs):
        track, noun, index, action = convert_bytes(kwargs['noun_adj'][1:-3]) - 1, kwargs['noun_adj'][3], convert_bytes(kwargs['noun_adj'][4:]) - 1, kwargs['verb']
        return self.verbs[action](track, noun, index)

    @undo_step
    def load_item(self, track, noun, index):

        if self.song().view.selected_track != self.song().tracks[track]:
            self.song().view.selected_track = self.song().tracks[track]
        item = list(self.browser_lists[noun].children)[index]
        self.browser.load_item(item)
        return 1
