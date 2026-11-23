class TimbreService:
    @staticmethod
    def clamp(value, min_value, max_value):
        return max(min_value, min(value, max_value))

    def find_device_parameter(self, track, keyword):
        for device in track.devices:
            for param in device.parameters:
                if keyword in param.name.lower():
                    return param
        return None

    def adjust_timbre(self, track, attribute, amount):
        if attribute is None or amount is None:
            return "error", {"message": "Missing timbre attribute/amount"}
        keyword = str(attribute).lower()
        param = self.find_device_parameter(track, keyword)
        if not param:
            return "error", {"message": f"No parameter found for {attribute}"}
        try:
            span = (param.max - param.min) if hasattr(param, "max") else 1.0
            delta = float(amount) * span * 0.2
            param.value = self.clamp(param.value + delta, param.min, param.max)
            return "ok", None
        except Exception as e:
            return "error", {"message": str(e)}
