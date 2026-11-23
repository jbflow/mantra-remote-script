class TargetResolver:
    def __init__(self):
        self._track_id_map = {}

    def register_track_id(self, track_id, track):
        if track_id is None or track is None:
            return
        self._track_id_map[str(track_id)] = track

    def resolve_track(self, song, target):
        if not song:
            return None

        if not isinstance(target, dict):
            return song.view.selected_track if hasattr(song, "view") else None

        track_id = target.get("track_id")
        if track_id is not None:
            mapped = self._track_id_map.get(str(track_id))
            if mapped is not None:
                return mapped

        role = target.get("role")
        if isinstance(role, str) and role.lower() == "master":
            return song.master_track if hasattr(song, "master_track") else None

        track_name = target.get("track_name")
        role_detail = target.get("role_detail")

        tracks = list(song.tracks) if hasattr(song, "tracks") else []
        return_tracks = list(song.return_tracks) if hasattr(song, "return_tracks") else []
        all_tracks = tracks + return_tracks

        if isinstance(track_name, str) and track_name:
            for track in all_tracks:
                if hasattr(track, "name") and track.name.lower() == track_name.lower():
                    return track

        if isinstance(role, str) and role:
            role_lower = role.lower()
            for track in all_tracks:
                name = track.name.lower() if hasattr(track, "name") else ""
                if name.startswith(role_lower) or role_lower in name:
                    return track

        if isinstance(role_detail, str) and role_detail:
            detail_lower = role_detail.lower()
            for track in all_tracks:
                name = track.name.lower() if hasattr(track, "name") else ""
                if detail_lower in name:
                    return track

        return song.view.selected_track if hasattr(song, "view") else None
