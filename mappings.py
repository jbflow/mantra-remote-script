from .Logging import logger
from .util import bars_beats_to_position


class ActionMappings:
    def __init__(self, control_surface, transport_actions, target_resolver):
        self._control_surface = control_surface
        self._transport = transport_actions
        self._targets = target_resolver

    @property
    def song(self):
        return self._control_surface.song()

    def dispatch_envelope(self, envelope):
        if not isinstance(envelope, dict):
            return "error", {"message": "Envelope must be an object"}

        domain = envelope.get("domain")
        intent = envelope.get("intent")
        if not domain or not isinstance(intent, dict):
            return "error", {"message": "Invalid envelope shape"}

        action = intent.get("action")
        if domain == "transport":
            return self._handle_transport(action, intent)
        if domain == "structure":
            return self._handle_structure(action, intent)
        if domain == "music":
            return self._handle_music(action, intent)
        if domain == "harmony":
            return self._handle_harmony(action, intent)
        if domain == "rhythm":
            return self._handle_rhythm(action, intent)
        if domain == "timbre":
            return self._handle_timbre(action, intent)
        return "error", {"message": f"Unsupported domain: {domain}"}

    def _handle_transport(self, action, payload):
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
            if action == "set_tempo":
                bpm = payload.get("bpm")
                if isinstance(bpm, (int, float)):
                    self._transport.set_tempo(bpm)
                    return "ok", None
                return "error", {"message": "Missing bpm"}
            if action == "metronome_on":
                self._transport.click_enable()
                return "ok", None
            if action == "metronome_off":
                self._transport.click_disable()
                return "ok", None
            if action == "loop_on":
                self._transport.loop_enable()
                return "ok", None
            if action == "loop_off":
                self._transport.loop_disable()
                return "ok", None
            if action == "set_loop":
                start_bars = payload.get("startBars")
                length_bars = payload.get("lengthBars")
                if isinstance(start_bars, int) and isinstance(length_bars, int):
                    signature = getattr(self.song, "signature_numerator", 4)
                    loop_start = bars_beats_to_position(start_bars, 1, signature)
                    loop_length = length_bars * signature
                    if loop_start is None:
                        return "error", {"message": "Invalid loop start"}
                    self.song.loop_start = loop_start
                    self.song.loop_length = loop_length
                    self.song.loop = 1
                    return "ok", None
                return "error", {"message": "Missing startBars/lengthBars"}
            if action == "locate":
                bars = payload.get("bars")
                beats = payload.get("beats")
                timecode = payload.get("timecode")
                if isinstance(timecode, str):
                    return "error", {"message": "Timecode locate not supported"}
                if isinstance(bars, int):
                    signature = getattr(self.song, "signature_numerator", 4)
                    position = bars_beats_to_position(bars, beats or 1, signature)
                    if position is None:
                        return "error", {"message": "Invalid locate position"}
                    if hasattr(self.song, "current_song_time"):
                        self.song.current_song_time = position
                        return "ok", None
                    return "error", {"message": "Song position not supported"}
        except Exception as exc:
            return "error", {"message": str(exc)}

        return "error", {"message": f"Unsupported transport action: {action}"}

    def _handle_structure(self, action, payload):
        target = payload.get("target") if isinstance(payload, dict) else None
        track = self._targets.resolve_track(self.song, target)
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
            if action == "select_track":
                self.song.view.selected_track = track
                return "ok", None
            if action == "arm_track":
                if hasattr(track, "can_arm") and not track.can_arm:
                    return "error", {"message": "Track cannot be armed"}
                track.arm = 1
                return "ok", None
            if action == "disarm_track":
                if hasattr(track, "can_arm") and not track.can_arm:
                    return "error", {"message": "Track cannot be disarmed"}
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
                return "error", {"message": "Unsupported action", "reason": "UNSUPPORTED_ACTION"}
        except Exception as exc:
            return "error", {"message": str(exc)}

        return "error", {"message": f"Unsupported structure action: {action}"}

    def _handle_music(self, action, payload):
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
                return self._set_key_signature(key, scale)
        except Exception as exc:
            return "error", {"message": str(exc)}

        return "error", {"message": f"Unsupported music action: {action}"}

    def _handle_harmony(self, action, payload):
        try:
            if action == "set_key":
                tonic = payload.get("tonic")
                scale = payload.get("scale")
                return self._set_key_signature(tonic, scale)
        except Exception as exc:
            return "error", {"message": str(exc)}

        return "error", {"message": f"Unsupported harmony action: {action}"}

    def _handle_rhythm(self, action, payload):
        try:
            if action == "set_swing" and hasattr(self.song, "swing_amount"):
                amount = payload.get("amount")
                if isinstance(amount, (int, float)):
                    self.song.swing_amount = float(amount)
                    return "ok", None
            return "error", {"message": f"Rhythm action not supported in Live API: {action}"}
        except Exception as exc:
            return "error", {"message": str(exc)}

    def _handle_timbre(self, action, payload):
        if action in ["adjust", "adjust_many"]:
            logger.info(f"Timbre action accepted: {action}")
            return "ok", None
        return "error", {"message": f"Unsupported timbre action: {action}"}

    def _set_key_signature(self, tonic, scale):
        if not hasattr(self.song, "scale_name") or not hasattr(self.song, "root_note"):
            return "error", {"message": "Key signature not supported", "reason": "UNSUPPORTED_ACTION"}

        root_note = self._note_to_semitone(tonic) if tonic is not None else None
        if root_note is not None:
            self.song.root_note = int(root_note)
        if isinstance(scale, str) and scale:
            self.song.scale_name = scale
        return "ok", None

    def _note_to_semitone(self, note):
        if isinstance(note, (int, float)):
            return int(note)
        if not isinstance(note, str):
            return None
        name = note.strip().lower()
        mapping = {
            "c": 0,
            "c#": 1,
            "db": 1,
            "d": 2,
            "d#": 3,
            "eb": 3,
            "e": 4,
            "f": 5,
            "f#": 6,
            "gb": 6,
            "g": 7,
            "g#": 8,
            "ab": 8,
            "a": 9,
            "a#": 10,
            "bb": 10,
            "b": 11,
        }
        return mapping.get(name)
