from __future__ import absolute_import, print_function, unicode_literals
from .mantra_surface import MantraSurface


def get_capabilities():
    return


def create_instance(c_instance):
    return MantraSurface(c_instance=c_instance)
