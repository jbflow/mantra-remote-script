from .DomainHandlers import (
    DomainServices,
    TransportHandler,
    StructureHandler,
    MusicHandler,
    HarmonyHandler,
    RhythmHandler,
    PerformanceHandler,
    TimbreHandler,
)


class IntentRouter:
    def __init__(self, control_surface, transport_actions, focus_state):
        self._control_surface = control_surface
        self._focus = focus_state
        self._services = DomainServices()
        self._handlers = {
            "transport": TransportHandler(control_surface, transport_actions, self._services),
            "structure": StructureHandler(control_surface, self._services),
            "music": MusicHandler(control_surface, self._services),
            "harmony": HarmonyHandler(control_surface, self._services),
            "rhythm": RhythmHandler(control_surface, self._services),
            "performance": PerformanceHandler(control_surface, self._services),
            "timbre": TimbreHandler(control_surface, self._services),
        }

    @property
    def song(self):
        return self._control_surface.song()

    def route_intent(self, intent):
        if not isinstance(intent, dict):
            return "error", {"message": "Intent must be an object"}
        domain = intent.get("domain")
        payload = intent.get("intent")
        if not domain or not isinstance(payload, dict):
            return "error", {"message": "Invalid intent shape"}

        action = payload.get("action")
        target = self._focus.resolve_target(payload)
        self._focus.update(domain=domain, target=target)

        handler = self._handlers.get(domain)
        if not handler:
            return "error", {"message": f"Unsupported domain: {domain}"}
        if domain in ["transport", "harmony", "rhythm"]:
            return handler.handle(action, payload)
        return handler.handle(action, payload, target)
