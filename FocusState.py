class FocusState:
    def __init__(self):
        self.last_target = None
        self.last_role = None
        self.last_domain = None

    def update(self, domain=None, target=None):
        if domain:
            self.last_domain = domain
        if target:
            self.last_target = target
            role = target.get("role") if isinstance(target, dict) else None
            if role:
                self.last_role = role

    def resolve_target(self, intent_payload):
        target = intent_payload.get("target") if isinstance(intent_payload, dict) else None
        if isinstance(target, dict):
            has_value = any(
                target.get(key)
                for key in ["role", "role_category", "role_detail", "track_name", "track_id"]
            )
            if has_value:
                return target
        return self.last_target
