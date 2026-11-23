from .TrackService import TrackService
from .KeyService import KeyService
from .TimbreService import TimbreService
from .BrowserService import BrowserService

track_service = TrackService()
key_service = KeyService()
timbre_service = TimbreService()
browser_service = BrowserService()


def find_track(song, target):
    return track_service.find_track(song, target)


def find_scene(song, scene_name):
    return track_service.find_scene(song, scene_name)


def find_clip_slot(track, clip_name):
    return track_service.find_clip_slot(track, clip_name)


def set_key_signature(song, key, scale):
    return key_service.set_key_signature(song, key, scale)


def adjust_timbre(track, attribute, amount):
    return timbre_service.adjust_timbre(track, attribute, amount)


def load_browser_device(control_surface, track, device_name, kind):
    return browser_service.load_browser_device(control_surface, track, device_name, kind)


__all__ = [
    "track_service",
    "key_service",
    "timbre_service",
    "browser_service",
    "find_track",
    "find_scene",
    "find_clip_slot",
    "set_key_signature",
    "adjust_timbre",
    "load_browser_device",
]
