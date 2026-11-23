class TransportActions:
    @staticmethod
    def clamp(value, min_value, max_value):
        return max(min_value, min(value, max_value))

    def __init__(self, c_instance):
        self._c_instance = c_instance
        self._song = c_instance.song()

    @property
    def song(self):
        return self._song

    def play(self):
        if hasattr(self.song, "is_playing") and self.song.is_playing:
            return
        if hasattr(self.song, "continue_playing"):
            self.song.continue_playing()
        elif hasattr(self.song, "start_playing"):
            self.song.start_playing()

    def stop(self):
        if hasattr(self.song, "stop_playing"):
            self.song.stop_playing()

    def record_enable(self):
        if hasattr(self.song, "record_mode"):
            self.song.record_mode = 1
        elif hasattr(self.song, "session_record"):
            self.song.session_record = 1

    def loop_enable(self):
        if hasattr(self.song, "loop"):
            self.song.loop = 1

    def loop_disable(self):
        if hasattr(self.song, "loop"):
            self.song.loop = 0

    def click_enable(self):
        if hasattr(self.song, "metronome"):
            self.song.metronome = 1

    def click_disable(self):
        if hasattr(self.song, "metronome"):
            self.song.metronome = 0

    def set_tempo(self, bpm):
        if hasattr(self.song, "tempo"):
            safe_bpm = self.clamp(float(bpm), 20.0, 999.0)
            self.song.tempo = safe_bpm
