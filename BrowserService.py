from .MatcherService import MatcherService


class BrowserService:
    def __init__(self, matcher=None):
        self._matcher = matcher or MatcherService()

    def load_browser_device(self, control_surface, track, device_name, kind):
        try:
            if control_surface.song().view.selected_track != track:
                control_surface.song().view.selected_track = track
            browser = control_surface.application().browser
            all_collections = [
                getattr(browser, "sounds", None),
                getattr(browser, "drums", None),
                getattr(browser, "instruments", None),
                getattr(browser, "audio_effects", None),
                getattr(browser, "midi_effects", None),
                getattr(browser, "plugins", None),
                getattr(browser, "samples", None),
                getattr(browser, "clips", None),
                getattr(browser, "packs", None),
                getattr(browser, "user_library", None),
                getattr(browser, "user_folders", None),
                getattr(browser, "current_project", None),
                getattr(browser, "max_for_live", None),
            ]
            all_collections = [c for c in all_collections if c is not None]

            if kind == "instrument":
                collections = [getattr(browser, "instruments", None), getattr(browser, "drums", None)]
            elif kind == "midi_effect":
                collections = [getattr(browser, "midi_effects", None)]
            elif kind == "effect":
                collections = [getattr(browser, "audio_effects", None)]
            else:
                collections = all_collections
            collections = [c for c in collections if c is not None]

            item = self.find_browser_item_any(collections, device_name)
            if not item:
                item = self.find_browser_item_any(all_collections, device_name)
            if item:
                browser.load_item(item)
                return "ok", None
            return "error", {"message": "Device not found in browser"}
        except Exception as e:
            return "error", {"message": str(e)}

    def find_browser_item(self, browser_item, name):
        query = str(name or "").strip()
        if not query:
            return None

        if "/" in query or ">" in query:
            return self.find_browser_path(browser_item, query)

        best_item = None
        best_score = 1.0
        query_tokens = [token for token in query.lower().replace("/", " ").split() if token]

        def walk(item):
            nonlocal best_item, best_score
            try:
                children = list(item.children)
            except Exception:
                children = []
            for child in children:
                try:
                    child_name = str(child.name)
                except Exception:
                    child_name = ""
                if not child_name:
                    continue
                if query.strip().lower() == child_name.strip().lower():
                    return child
                is_loadable = bool(getattr(child, "is_loadable", False))
                name_lower = child_name.strip().lower()
                if is_loadable:
                    if not query_tokens or all(token in name_lower for token in query_tokens):
                        score = self._matcher.normalized_distance(query, child_name)
                        if score < best_score:
                            best_score = score
                            best_item = child
                if hasattr(child, "children") and len(child.children) > 0:
                    found = walk(child)
                    if found:
                        return found
            return None

        exact_or_partial = walk(browser_item)
        if exact_or_partial:
            return exact_or_partial
        if best_item and best_score <= 0.4:
            return best_item
        return None

    def find_browser_path(self, browser_item, name):
        parts = [part.strip() for part in str(name).replace(">", "/").split("/") if part.strip()]
        if not parts:
            return None

        current = browser_item
        for part in parts:
            try:
                children = list(current.children)
            except Exception:
                children = []
            if not children:
                return None

            exact = None
            for child in children:
                try:
                    child_name = str(child.name).strip()
                except Exception:
                    child_name = ""
                if child_name.lower() == part.lower():
                    exact = child
                    break

            if exact is None:
                exact = self._matcher.best_match(part, children, key=lambda item: getattr(item, "name", ""), threshold=0.35)
            if exact is None:
                return None
            current = exact

        if getattr(current, "is_loadable", False):
            return current
        return self.find_first_loadable(current)

    def find_first_loadable(self, browser_item):
        try:
            children = list(browser_item.children)
        except Exception:
            children = []
        for child in children:
            if getattr(child, "is_loadable", False):
                return child
            found = self.find_first_loadable(child)
            if found:
                return found
        return None

    def find_browser_item_any(self, collections, name):
        if not collections:
            return None
        for collection in collections:
            found = self.find_browser_item(collection, name)
            if found:
                return found
        return None
