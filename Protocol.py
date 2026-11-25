import json
import uuid

try:
    from .Logging import logger
except ImportError:
    import logging
    logger = logging.getLogger("mantra")

class Protocol:
    def __init__(self, interpreter):
        self.interpreter = interpreter

    def parse_message(self, text):
        try:
            msg = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None, {'type': 'error', 'code': 'BAD_REQUEST', 'message': 'Invalid JSON'}

        msg_type = msg.get('type')
        if msg_type == 'ping':
            return 'ping', {'type': 'pong'}
        elif msg_type == 'intent':
            return self._handle_intent(msg)
        else:
            return None, {'type': 'error', 'code': 'BAD_REQUEST', 'message': 'Unknown message type'}

    def _handle_intent(self, msg):
        try:
            payload = msg.get('payload')
            if not payload:
                return None, {'type': 'error', 'code': 'BAD_REQUEST', 'message': 'Missing payload'}

            if isinstance(payload, dict):
                envelopes = [payload]
            elif isinstance(payload, list):
                envelopes = payload
            else:
                return None, {'type': 'error', 'code': 'BAD_REQUEST', 'message': 'payload must be dict or list'}

            processed = []
            for env in envelopes:
                if not isinstance(env, dict):
                    return None, {'type': 'error', 'code': 'BAD_REQUEST', 'message': 'envelope must be dict'}
                if 'id' not in env:
                    env['id'] = str(uuid.uuid4())
                processed.append(env)

            ids = [e['id'] for e in processed]
            results = self.interpreter.execute_batch(processed)

            ack = {'type': 'ack', 'ids': ids, 'status': 'accepted'}
            return 'intent', {'ack': ack, 'results': results}

        except Exception as e:
            logger.error(f'Error handling intent: {e}')
            return None, {'type': 'error', 'code': 'INTERNAL_ERROR', 'message': str(e)}
