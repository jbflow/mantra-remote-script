from __future__ import absolute_import, print_function, unicode_literals
from .Mantra import Mantra
from ableton.v2.control_surface.capabilities import SUGGESTED_PORT_NAMES_KEY

def get_capabilities():
    return

def create_instance(c_instance):
    return Mantra(c_instance=c_instance)
