import Live
import queue
import uuid
from _Framework.ControlSurface import ControlSurface
from .Socket import Socket
from .Logging import logger
from .TransportActions import TransportActions
from .FocusState import FocusState
from .IntentRouter import IntentRouter


class Mantra(ControlSurface):
    def __init__(self, c_instance, *a, **k):
        super(Mantra, self).__init__(c_instance, *a, **k)
        self._c_instance = c_instance
        with self.component_guard():
            self.socket = Socket(c_instance, self.socket_callback)
            self.socket.start()
            self._transport = TransportActions(c_instance)
            self.message_queue = queue.Queue()
            self.focus_state = FocusState()
            self.intent_router = IntentRouter(self, self._transport, self.focus_state)

        self.check_queue = Live.Base.Timer(callback=self.process_queue, interval=20, repeat=True)
        self.check_queue.start()

    def disconnect(self):
        logger.info("Disconnecting")
        self.check_queue.stop()
        self.socket.send_json({"type": "disconnect"})
        if self.socket.connection:
            self.socket.connection.close()
        self.socket.socket.close()
        super(Mantra, self).disconnect()

    def socket_callback(self, message):
        logger.info(f'Socket callback invoked with: {message}')
        self.message_queue.put(message)

    def process_queue(self):
        while not self.message_queue.empty():
            message = self.message_queue.get()
            if isinstance(message, dict):
                self._handle_intent_message(message)

    def _handle_intent_message(self, message):
        msg_type = message.get("type")
        if msg_type == "ping":
            self.socket.send_json({"type": "pong"})
            return

        if msg_type == "focus":
            target = message.get("target")
            if isinstance(target, dict):
                self.focus_state.update(domain=None, target=target)
                self.socket.send_json({"type": "ack", "ids": []})
            else:
                self._send_error("BAD_REQUEST", "Invalid focus target")
            return

        if msg_type != "intent":
            self._send_error("BAD_REQUEST", "Unsupported message type")
            return

        payload = message.get("payload")
        intents = payload if isinstance(payload, list) else [payload]
        ids = []

        for intent in intents:
            intent_id = (
                str(intent.get("id")) if isinstance(intent, dict) and intent.get("id") else str(uuid.uuid4())
            )
            ids.append(intent_id)
            status, details = self.intent_router.route_intent(intent)
            if status == "ok":
                self.socket.send_json({"type": "result", "id": intent_id, "status": "ok"})
            else:
                self.socket.send_json({
                    "type": "result",
                    "id": intent_id,
                    "status": "error",
                    "details": details
                })

        self.socket.send_json({"type": "ack", "ids": ids, "status": "accepted"})

    def _send_error(self, code, message, issues=None):
        payload = {"type": "error", "code": code, "message": message}
        if issues:
            payload["issues"] = issues
        self.socket.send_json(payload)


