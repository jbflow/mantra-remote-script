from .TrackService import TrackService
from .KeyService import KeyService
from .TimbreService import TimbreService
from .BrowserService import BrowserService


class DomainServices:
    def __init__(self):
        self.track = TrackService()
        self.key = KeyService()
        self.timbre = TimbreService()
        self.browser = BrowserService()


class BaseDomainHandler:
    def __init__(self, control_surface, services):
        self._control_surface = control_surface
        self._services = services

    @property
    def song(self):
        return self._control_surface.song()


class TransportHandler(BaseDomainHandler):
    def __init__(self, control_surface, transport_actions, services):
        super(TransportHandler, self).__init__(control_surface, services)
        self._transport = transport_actions

    def handle(self, action, payload):
        try:
            if action == "play":
                self._transport.play()
                return "ok", None
            if action == "stop":
                self._transport.stop()
                return "ok", None
            if action == "record":
                self._transport.record_enable()
                return "ok", None
            if action == "toggle_record":
                self.song.record_mode = 0 if self.song.record_mode else 1
                return "ok", None
            if action == "loop_on":
                self._transport.loop_enable()
                return "ok", None
            if action == "loop_off":
                self._transport.loop_disable()
                return "ok", None
            if action == "metronome_on":
                self._transport.click_enable()
                return "ok", None
            if action == "metronome_off":
                self._transport.click_disable()
                return "ok", None
            if action == "set_tempo":
                bpm = payload.get("bpm")
                if isinstance(bpm, (int, float)):
                    self._transport.set_tempo(bpm)
                    return "ok", None
                return "error", {"message": "Missing bpm"}
            if action == "set_time_signature":
                numerator = payload.get("numerator")
                denominator = payload.get("denominator")
                if isinstance(numerator, int) and isinstance(denominator, int):
                    self.song.signature_numerator = numerator
                    self.song.signature_denominator = denominator
                    return "ok", None
                return "error", {"message": "Missing numerator/denominator"}
            if action == "locate":
                bars = payload.get("bars")
                beats = payload.get("beats") or 1
                timecode = payload.get("timecode")
                if isinstance(timecode, str):
                    return "error", {"message": "Timecode locate not supported"}
                if isinstance(bars, int):
                    signature = self.song.signature_numerator
                    beat_position = ((bars - 1) * signature) + max(0, beats - 1)
                    if hasattr(self.song, "current_song_time"):
                        self.song.current_song_time = beat_position
                        return "ok", None
                    return "error", {"message": "Song position not supported"}
            if action == "set_loop":
                start_bars = payload.get("startBars")
                length_bars = payload.get("lengthBars")
                if isinstance(start_bars, int) and isinstance(length_bars, int):
                    signature = self.song.signature_numerator
                    self.song.loop_start = (start_bars - 1) * signature
                    self.song.loop_length = length_bars * signature
                    self.song.loop = 1
                    return "ok", None
                return "error", {"message": "Missing startBars/lengthBars"}
        except Exception as e:
            return "error", {"message": str(e)}

        return "error", {"message": f"Unsupported transport action: {action}"}


class StructureHandler(BaseDomainHandler):
    def handle(self, action, payload, target):
        track = self._services.track.find_track(self.song, target)
        try:
            if action == "create_track":
                track_type = payload.get("type")
                index = len(self.song.tracks) if hasattr(self.song, "tracks") else 0
                if track_type == "midi":
                    try:
                        self.song.create_midi_track(index)
                    except TypeError:
                        self.song.create_midi_track()
                else:
                    try:
                        self.song.create_audio_track(index)
                    except TypeError:
                        self.song.create_audio_track()
                role = payload.get("role")
                if role and hasattr(self.song, "tracks") and len(self.song.tracks) > 0:
                    self.song.tracks[-1].name = str(role).capitalize()
                return "ok", None
            if not track:
                return "error", {"message": "Target track not found"}
            if action == "rename_track":
                name = payload.get("name") or payload.get("new_name")
                if not name:
                    return "error", {"message": "Missing track name"}
                track.name = str(name)
                return "ok", None
            if action == "delete_track":
                track_type, index = self._services.track.locate_track(self.song, track)
                if track_type == "track":
                    self.song.delete_track(index)
                    return "ok", None
                if track_type == "return" and hasattr(self.song, "delete_return_track"):
                    self.song.delete_return_track(index)
                    return "ok", None
                return "error", {"message": "Track cannot be deleted"}
            if action == "duplicate_track":
                track_type, index = self._services.track.locate_track(self.song, track)
                if track_type == "track" and hasattr(self.song, "duplicate_track"):
                    self.song.duplicate_track(index)
                    return "ok", None
                return "error", {"message": "Track cannot be duplicated"}
            if action == "select_track":
                self.song.view.selected_track = track
                return "ok", None
            if action == "arm_track":
                track.arm = 1
                return "ok", None
            if action == "disarm_track":
                track.arm = 0
                return "ok", None
            if action == "mute":
                track.mute = 1
                return "ok", None
            if action == "unmute":
                track.mute = 0
                return "ok", None
            if action == "solo":
                track.solo = 1
                return "ok", None
            if action == "unsolo":
                track.solo = 0
                return "ok", None
            if action == "load_device":
                device_name = payload.get("device")
                kind = payload.get("kind")
                if not device_name:
                    return "error", {"message": "Missing device name"}
                return self._services.browser.load_browser_device(
                    self._control_surface, track, device_name, kind
                )
        except Exception as e:
            return "error", {"message": str(e)}

        return "error", {"message": f"Unsupported structure action: {action}"}


class MusicHandler(BaseDomainHandler):
    def handle(self, action, payload, target):
        try:
            if action == "quantize":
                strength = payload.get("strength", 0.8)
                clip = self.song.view.detail_clip if hasattr(self.song.view, "detail_clip") else None
                if clip and getattr(clip, "is_midi_clip", False) and hasattr(clip, "quantize"):
                    clip.quantize(float(strength), 1.0)
                    return "ok", None
                return "error", {"message": "No MIDI clip selected for quantize"}
            if action == "transpose":
                semitones = payload.get("semitones")
                clip = self.song.view.detail_clip if hasattr(self.song.view, "detail_clip") else None
                if clip and getattr(clip, "is_midi_clip", False) and hasattr(clip, "transpose"):
                    clip.transpose(int(semitones))
                    return "ok", None
                return "error", {"message": "No MIDI clip selected for transpose"}
            if action == "set_key_signature":
                key = payload.get("key")
                scale = payload.get("scale")
                return self._services.key.set_key_signature(self.song, key, scale)
        except Exception as e:
            return "error", {"message": str(e)}

        return "error", {"message": f"Unsupported music action: {action}"}


class HarmonyHandler(BaseDomainHandler):
    def handle(self, action, payload):
        try:
            if action == "set_key":
                tonic = payload.get("tonic")
                scale = payload.get("scale")
                return self._services.key.set_key_signature(self.song, tonic, scale)
            if action in ["set_chord", "set_chord_progression", "set_pitch_range"]:
                return "error", {"message": f"Harmony action not supported in Live API: {action}"}
        except Exception as e:
            return "error", {"message": str(e)}

        return "error", {"message": f"Unsupported harmony action: {action}"}


class RhythmHandler(BaseDomainHandler):
    def handle(self, action, payload):
        try:
            if action == "set_swing" and hasattr(self.song, "swing_amount"):
                amount = payload.get("amount")
                if isinstance(amount, (int, float)):
                    self.song.swing_amount = float(amount)
                    return "ok", None
            return "error", {"message": f"Rhythm action not supported in Live API: {action}"}
        except Exception as e:
            return "error", {"message": str(e)}


class PerformanceHandler(BaseDomainHandler):
    def handle(self, action, payload, target):
        try:
            if action == "trigger_scene":
                scene_name = payload.get("scene_name")
                scene = self._services.track.find_scene(self.song, scene_name)
                if scene:
                    scene.fire()
                    return "ok", None
                return "error", {"message": "Scene not found"}
            if action == "trigger_clip":
                clip_name = payload.get("clip_name")
                track = self._services.track.find_track(self.song, target)
                if not track:
                    return "error", {"message": "Target track not found"}
                clip_slot = self._services.track.find_clip_slot(track, clip_name)
                if clip_slot:
                    clip_slot.fire()
                    return "ok", None
                return "error", {"message": "Clip not found"}
        except Exception as e:
            return "error", {"message": str(e)}

        return "error", {"message": f"Unsupported performance action: {action}"}


class TimbreHandler(BaseDomainHandler):
    def handle(self, action, payload, target):
        try:
            track = self._services.track.find_track(self.song, target)
            if not track:
                return "error", {"message": "Target track not found"}
            if action == "adjust":
                attribute = payload.get("attribute")
                amount = payload.get("amount")
                return self._services.timbre.adjust_timbre(track, attribute, amount)
            if action == "adjust_many":
                changes = payload.get("changes")
                if not isinstance(changes, list):
                    return "error", {"message": "Missing changes array"}
                for change in changes:
                    attribute = change.get("attribute") if isinstance(change, dict) else None
                    amount = change.get("amount") if isinstance(change, dict) else None
                    self._services.timbre.adjust_timbre(track, attribute, amount)
                return "ok", None
        except Exception as e:
            return "error", {"message": str(e)}

        return "error", {"message": f"Unsupported timbre action: {action}"}
