class KeyService:
    NOTE_TO_ROOT = {
        "C": 0,
        "C#": 1,
        "DB": 1,
        "D": 2,
        "D#": 3,
        "EB": 3,
        "E": 4,
        "F": 5,
        "F#": 6,
        "GB": 6,
        "G": 7,
        "G#": 8,
        "AB": 8,
        "A": 9,
        "A#": 10,
        "BB": 10,
        "B": 11,
    }

    def set_key_signature(self, song, key, scale):
        if not key:
            return "error", {"message": "Missing key/tonic"}
        root = self.NOTE_TO_ROOT.get(str(key).upper())
        if root is None:
            return "error", {"message": "Invalid key"}
        try:
            if hasattr(song, "root_note"):
                song.root_note = int(root)
            if scale and hasattr(song, "scale_name"):
                song.scale_name = str(scale)
            return "ok", None
        except Exception as e:
            return "error", {"message": str(e)}
