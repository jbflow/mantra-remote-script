class TrackService:
    def find_track(self, song, target):
        if not target:
            return song.view.selected_track if hasattr(song.view, "selected_track") else None
        track_name = target.get("track_name") if isinstance(target, dict) else None
        role = target.get("role") if isinstance(target, dict) else None
        role_detail = target.get("role_detail") if isinstance(target, dict) else None
        role_category = target.get("role_category") if isinstance(target, dict) else None
        tracks = list(song.tracks)
        visible_tracks = list(song.visible_tracks) if hasattr(song, "visible_tracks") else tracks
        return_tracks = list(song.return_tracks) if hasattr(song, "return_tracks") else []
        all_tracks = tracks + return_tracks

        if isinstance(role, str) and role.lower() == "master":
            return song.master_track if hasattr(song, "master_track") else None

        if isinstance(track_name, int):
            index = int(track_name) - 1
            if 0 <= index < len(visible_tracks):
                return visible_tracks[index]
            if 0 <= index < len(all_tracks):
                return all_tracks[index]

        if isinstance(track_name, str) and track_name.strip().isdigit():
            index = int(track_name.strip()) - 1
            if 0 <= index < len(visible_tracks):
                return visible_tracks[index]
            if 0 <= index < len(all_tracks):
                return all_tracks[index]

        if track_name:
            for track in all_tracks:
                if track.name.lower() == track_name.lower():
                    return track
        if role:
            for track in all_tracks:
                if role.lower() in track.name.lower():
                    return track
        if role_category:
            for track in all_tracks:
                if role_category.lower() in track.name.lower():
                    return track
        if role_detail:
            for track in all_tracks:
                if role_detail.lower() in track.name.lower():
                    return track
        return song.view.selected_track if hasattr(song.view, "selected_track") else None

    def find_scene(self, song, scene_name):
        scenes = list(song.scenes)
        if isinstance(scene_name, int):
            index = scene_name - 1
            return scenes[index] if 0 <= index < len(scenes) else None
        if isinstance(scene_name, str):
            for scene in scenes:
                if scene.name.lower() == scene_name.lower():
                    return scene
        return None

    def locate_track(self, song, track):
        if track is None:
            return None, None
        tracks = list(song.tracks) if hasattr(song, "tracks") else []
        if track in tracks:
            return "track", tracks.index(track)
        return_tracks = list(song.return_tracks) if hasattr(song, "return_tracks") else []
        if track in return_tracks:
            return "return", return_tracks.index(track)
        return None, None

    def find_clip_slot(self, track, clip_name):
        if clip_name is None:
            return None
        if isinstance(clip_name, int):
            index = clip_name - 1
            if 0 <= index < len(track.clip_slots):
                return track.clip_slots[index]
        if isinstance(clip_name, str):
            for slot in track.clip_slots:
                if slot.has_clip and slot.clip.name.lower() == clip_name.lower():
                    return slot
        return None
