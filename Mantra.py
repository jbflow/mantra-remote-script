import Live
import queue
import json
from _Framework.ControlSurface import ControlSurface
from ableton.v3.base import nop
from .Socket import Socket
from .Protocol import Protocol
from . import handlers
from .Logging import logger

class Mantra(ControlSurface):
    def __init__(self, c_instance, *a, **k):
        super(Mantra, self).__init__(c_instance, *a, **k)
        self._c_instance = c_instance
        with self.component_guard():
            self.protocol = Protocol(self)
            self.socket = Socket(c_instance, self.socket_callback)
            self.socket.start()
            self.message_queue = queue.Queue()
            self.check_queue = Live.Base.Timer(callback=self.process_queue, interval=20, repeat=True)
            self.check_queue.start()

    def disconnect(self):
        logger.info("Disconnecting")
        self.check_queue.stop()
        self.socket.disconnect()
        super(Mantra, self).disconnect()

    def execute_batch(self, envelopes):
        return handlers.execute_batch(envelopes, self.song(), self.application())

    def socket_callback(self, msg_text):
        logger.info(f'Socket callback invoked with: {msg_text}')
        self.message_queue.put(msg_text)

    def process_queue(self):
        while not self.message_queue.empty():
            msg_text = self.message_queue.get()
            self._handle_message(msg_text)

    def _handle_message(self, msg_text):
        try:
            msg_type, response = self.protocol.parse_message(msg_text)
            
            if msg_type == 'ping':
                self.socket.send_message(json.dumps(response))
            elif msg_type == 'intent':
                ack = response['ack']
                results = response['results']
                self.socket.send_message(json.dumps(ack))
                for result in results:
                    self.socket.send_message(json.dumps({'type': 'result', **result}))
            else:
                self.socket.send_message(json.dumps(response))
        except Exception as e:
            logger.error(f'Error processing message: {e}')
            self.socket.send_message(json.dumps({'type': 'error', 'code': 'INTERNAL_ERROR', 'message': str(e)}))
