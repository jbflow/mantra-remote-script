try:
    from ..Logging import logger
except (ImportError, ValueError):
    import logging
    logger = logging.getLogger("mantra")

from .common import ActionError
from .parameters import ParametersHandler
from .performance import PerformanceHandler
from .structure import StructureHandler
from .transport import TransportHandler

REGISTRY = {
    'transport': TransportHandler(),
    'structure': StructureHandler(),
    'performance': PerformanceHandler(),
    'parameters': ParametersHandler(),
}


def execute_batch(envelopes, song, application):
    """Runs envelopes in order inside one undo step, so the whole batch undoes as a unit."""
    song.begin_undo_step()
    try:
        return [_execute(envelope, song, application) for envelope in envelopes]
    finally:
        song.end_undo_step()


def _error(envelope_id, message):
    return {'id': envelope_id, 'status': 'error', 'details': {'message': message}}


def _execute(envelope, song, application):
    envelope_id = envelope.get('id')
    domain, intent = envelope.get('domain'), envelope.get('intent')
    action = intent.get('action') if isinstance(intent, dict) else None
    if not isinstance(domain, str) or not isinstance(action, str):
        return _error(envelope_id, 'invalid envelope: expected domain and intent.action')
    handler = REGISTRY.get(domain)
    if handler is None or not handler.supports(action):
        return _error(envelope_id, 'unsupported action: %s.%s' % (domain, action))
    payload = {key: value for key, value in intent.items() if key not in ('action', 'target')}
    try:
        status, details = handler.handle(action, payload, intent.get('target'), song, application)
    except ActionError as e:
        return _error(envelope_id, str(e))
    except Exception as e:
        logger.error('%s.%s failed: %s' % (domain, action, e))
        return _error(envelope_id, str(e))
    result = {'id': envelope_id, 'status': status}
    if details:
        result['details'] = details
    return result
