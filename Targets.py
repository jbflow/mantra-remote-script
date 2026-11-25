from collections import deque


class ActionError(Exception):
    """A request that cannot be carried out; the message is reported back in the result."""


TARGET_KEYS = ('track_name', 'track_id', 'role', 'role_category', 'role_detail')

BROWSER_ALL = ('sounds', 'drums', 'instruments', 'audio_effects', 'midi_effects', 'plugins', 'samples',
               'clips', 'packs', 'user_library', 'user_folders', 'current_project', 'max_for_live')
BROWSER_BY_KIND = {
    'instrument': ('instruments', 'drums'),
    'effect': ('audio_effects', 'midi_effects'),
}
MATCH_THRESHOLD = 0.4
MAX_BROWSER_NODES = 5000


# ---------------------------------------------------------------- fuzzy matching

def levenshtein_distance(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def normalized_distance(a, b):
    return levenshtein_distance(a, b) / float(max(len(a), len(b), 1))


def match_score(query, candidate):
    """0 is an exact (case-insensitive) match, 1 is unrelated. Lower is better."""
    query = str(query).strip().lower()
    candidate = str(candidate or '').strip().lower()
    if not query or not candidate:
        return 1.0
    if query == candidate:
        return 0.0
    tokens = query.replace('/', ' ').split()
    distance = normalized_distance(query, candidate)
    if tokens and all(token in candidate for token in tokens):
        return 0.1 + 0.1 * distance
    return distance


def best_match(query, candidates, key=lambda item: item, threshold=MATCH_THRESHOLD):
    best, best_score = None, threshold
    for item in candidates:
        score = match_score(query, key(item))
        if score == 0.0:
            return item
        if score <= best_score:
            best, best_score = item, score
    return best


# ---------------------------------------------------------------- tracks

def _present(value):
    return value is not None and value != ''


def _is_index(value):
    if isinstance(value, bool):
        return False
    return isinstance(value, int) or (isinstance(value, str) and value.strip().isdigit())


def _match_name(tracks, text, partial=True):
    """Exact name first, then (if partial) name containing the text; underscores read as spaces."""
    variants = {str(text).strip().lower(), str(text).strip().lower().replace('_', ' ')}
    for track in tracks:
        if track.name.strip().lower() in variants:
            return track
    if not partial:
        return None
    for track in tracks:
        name = track.name.lower()
        if any(v and v in name for v in variants):
            return track
    return None


def find_track(song, target):
    """Resolve a TargetRef to a Live track.

    No identifying field at all means the selected track. A target that names something which cannot
    be found is an error, so destructive actions never land on the selected track by accident.
    """
    ref = target if isinstance(target, dict) else {}
    if not any(_present(ref.get(key)) for key in TARGET_KEYS):
        track = song.view.selected_track
        if track is None:
            raise ActionError('no track selected')
        return track

    role = ref.get('role')
    if isinstance(role, str) and role.strip().lower() == 'master':
        return song.master_track

    pool = list(song.visible_tracks) + list(song.return_tracks)
    name = ref.get('track_name')
    if _present(name):
        if isinstance(name, str):
            found = _match_name(pool + [song.master_track], name, partial=False)
            if found is not None:
                return found
        if _is_index(name):
            index = int(name) - 1
            if 0 <= index < len(pool):
                return pool[index]
        elif isinstance(name, str):
            found = _match_name(pool, name)
            if found is not None:
                return found
    for key in ('role', 'role_category', 'role_detail'):
        if _present(ref.get(key)):
            found = _match_name(pool, ref[key])
            if found is not None:
                return found
    raise ActionError('target track not found: %s' % {k: ref[k] for k in TARGET_KEYS if _present(ref.get(k))})


def locate_track(song, track):
    """('track' | 'return' | 'master', index) for a Live track object."""
    tracks = list(song.tracks)
    if track in tracks:
        return 'track', tracks.index(track)
    returns = list(song.return_tracks)
    if track in returns:
        return 'return', returns.index(track)
    if track == song.master_track:
        return 'master', None
    raise ActionError('track is not part of the song')


# ---------------------------------------------------------------- scenes and clips

def _by_position_or_name(items, ref, name_of, what):
    if _is_index(ref):
        index = int(ref) - 1
        if 0 <= index < len(items):
            return items[index]
    elif isinstance(ref, str):
        text = ref.strip().lower()
        for item in items:
            if name_of(item).strip().lower() == text:
                return item
    raise ActionError('%s not found: %s' % (what, ref))


def find_scene(song, scene_name):
    return _by_position_or_name(list(song.scenes), scene_name, lambda scene: scene.name, 'scene')


def find_clip_slot(track, clip_name):
    """Slot holding the clip with this name (or the 1-based slot number)."""
    slots = [slot for slot in track.clip_slots if slot.has_clip]
    if _is_index(clip_name):
        index = int(clip_name) - 1
        all_slots = list(track.clip_slots)
        if 0 <= index < len(all_slots) and all_slots[index].has_clip:
            return all_slots[index]
        raise ActionError('clip not found: %s' % clip_name)
    return _by_position_or_name(slots, clip_name, lambda slot: slot.clip.name, 'clip')


# ---------------------------------------------------------------- browser

def _children(item):
    try:
        return list(item.children)
    except Exception:
        return []


def _collections(browser, names):
    found = (getattr(browser, name, None) for name in names)
    return [collection for collection in found if collection is not None]


def _find_path(collections, query):
    parts = [part.strip() for part in query.replace('>', '/').split('/') if part.strip()]
    for root in collections:
        names = list(parts)
        if names and str(root.name).strip().lower() == names[0].lower():
            names = names[1:]
        current = root
        for part in names:
            current = best_match(part, _children(current), key=lambda item: item.name, threshold=0.35)
            if current is None:
                break
        if current is None or current is root:
            continue
        found = _first_loadable(current)
        if found is not None:
            return found
    return None


def _first_loadable(item):
    if getattr(item, 'is_loadable', False):
        return item
    for child in _children(item):
        found = _first_loadable(child)
        if found is not None:
            return found
    return None


def _search(collections, query):
    """Breadth-first over the browser tree, so shallow matches win and huge libraries stay bounded."""
    best, best_score = None, MATCH_THRESHOLD
    pending, visited = deque(collections), 0
    while pending and visited < MAX_BROWSER_NODES:
        for child in _children(pending.popleft()):
            visited += 1
            if getattr(child, 'is_loadable', False):
                score = match_score(query, child.name)
                if score == 0.0:
                    return child
                if score < best_score:
                    best, best_score = child, score
            pending.append(child)
    return best


def find_browser_item(browser, query, kind=None):
    """Loadable browser item for a device name or a 'Folder/Sub/Name' path.

    Looks in the collections for the kind first, then in the whole browser.
    """
    query = str(query or '').strip()
    if not query:
        raise ActionError('missing device name')
    find = _find_path if ('/' in query or '>' in query) else _search
    groups = []
    if kind in BROWSER_BY_KIND:
        groups.append(BROWSER_BY_KIND[kind])
    groups.append(BROWSER_ALL)
    for names in groups:
        found = find(_collections(browser, names), query)
        if found is not None:
            return found
    raise ActionError('device not found in browser: %s' % query)
