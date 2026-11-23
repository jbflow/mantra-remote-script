import Live
from _Framework.ControlSurface import ControlSurface

from .Logging import logger
from .TransportActions import TransportActions
from .dispatcher import DispatchQueue
from .FocusState import FocusState
from .IntentRouter import IntentRouter
from .ws_client import WebSocketClient


DEFAULT_WS_URL = "ws://localhost:1979/interpreter"


class MantraSurface(ControlSurface):
    def __init__(self, c_instance, *a, **k):
        super(MantraSurface, self).__init__(c_instance, *a, **k)
        self._c_instance = c_instance

        with self.component_guard():
            self._transport = TransportActions(c_instance)
            self._queue = DispatchQueue()
            self._focus_state = FocusState()
            self._intent_router = IntentRouter(self, self._transport, self._focus_state)
            self._ws = WebSocketClient(DEFAULT_WS_URL, self._queue.put, self._on_status)
            self._ws.start()

        self._timer = Live.Base.Timer(callback=self._process_queue, interval=20, repeat=True)
        self._timer.start()

    def disconnect(self):
        logger.info("Disconnecting MantraSurface")
        self._timer.stop()
        self._ws.stop()
        super(MantraSurface, self).disconnect()

    def _on_status(self, status):
        logger.info(f"WebSocket status: {status}")
        if status == "connected":
            self._send_register()

    def _send_register(self):
        capabilities = {
            "domains": ["transport", "structure", "music", "harmony", "rhythm", "timbre"],
            "actions": {
                "transport": [
                    "play",
                    "stop",
                    "record",
                    "toggle_record",
                    "set_tempo",
                    "set_time_signature",
                    "metronome_on",
                    "metronome_off",
                    "loop_on",
                    "loop_off",
                    "set_loop",
                    "locate",
                ],
                "structure": [
                    "create_track",
                    "select_track",
                    "arm_track",
                    "disarm_track",
                    "mute",
                    "unmute",
                    "solo",
                    "unsolo",
                    "rename_track",
                    "delete_track",
                    "duplicate_track",
                    "load_device",
                ],
                "music": ["quantize", "transpose", "set_key_signature"],
                "harmony": ["set_key"],
                "rhythm": ["set_swing"],
                "timbre": ["adjust", "adjust_many"],
            },
        }

        payload = {
            "type": "register",
            "interpreter": "ableton",
            "version": "0.1",
            "capabilities": capabilities,
        }
        self._ws.send_json(payload)

    def _process_queue(self):
        self._queue.drain(self._handle_message)

    def _handle_message(self, message):
        if not isinstance(message, dict):
            return

        msg_type = message.get("type")
        if msg_type == "ping":
            self._ws.send_json({"type": "pong"})
            return

        if msg_type != "dispatch":
            logger.info(f"Ignoring unsupported message type: {msg_type}")
            return

        envelope = message.get("payload")
        if not isinstance(envelope, dict):
            logger.error("Dispatch payload missing envelope")
            return

        envelope_id = envelope.get("id")
        status, details = self._intent_router.route_intent(envelope)
        result = {"type": "result", "id": envelope_id, "status": status}
        if details:
            result["details"] = details
        self._ws.send_json(result)
