"""Test the JSON protocol over WebSocket."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from Protocol import Protocol
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location("Protocol", Path(__file__).parent.parent / "Protocol.py")
    Protocol_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(Protocol_module)
    Protocol = Protocol_module.Protocol

class FakeLogger:
    def error(self, msg):
        pass
    def warning(self, msg):
        pass
    def info(self, msg):
        pass

class FakeInterpreter:
    def __init__(self):
        self.calls = []

    def execute_batch(self, envelopes):
        self.calls.append(envelopes)
        results = []
        for env in envelopes:
            results.append({
                'id': env.get('id'),
                'status': 'ok',
                'details': {'message': 'fake response'}
            })
        return results

def test_ping_pong():
    """Test ping/pong handshake."""
    interpreter = FakeInterpreter()
    protocol = Protocol(interpreter)
    
    msg_type, response = protocol.parse_message(json.dumps({'type': 'ping'}))
    assert msg_type == 'ping'
    assert response == {'type': 'pong'}

def test_intent_with_id():
    """Test intent message processing with explicit id."""
    interpreter = FakeInterpreter()
    protocol = Protocol(interpreter)
    
    test_id = 'test-id-12345'
    intent = {
        'type': 'intent',
        'payload': {
            'id': test_id,
            'domain': 'transport',
            'intent': 'play'
        },
        'source': 'ui'
    }
    
    msg_type, response = protocol.parse_message(json.dumps(intent))
    assert msg_type == 'intent'
    assert response['ack']['ids'] == [test_id]
    assert response['ack']['status'] == 'accepted'
    assert len(response['results']) == 1
    assert response['results'][0]['id'] == test_id
    assert response['results'][0]['status'] == 'ok'

def test_intent_without_id_generates_one():
    """Test that id is generated if missing."""
    interpreter = FakeInterpreter()
    protocol = Protocol(interpreter)
    
    intent = {
        'type': 'intent',
        'payload': {
            'domain': 'transport',
            'intent': 'play'
        },
        'source': 'ui'
    }
    
    msg_type, response = protocol.parse_message(json.dumps(intent))
    assert msg_type == 'intent'
    assert len(response['ack']['ids']) == 1
    assert response['results'][0]['id'] == response['ack']['ids'][0]

def test_intent_with_multiple_envelopes():
    """Test batch intent processing."""
    interpreter = FakeInterpreter()
    protocol = Protocol(interpreter)
    
    id1 = 'test-id-1'
    id2 = 'test-id-2'
    intent = {
        'type': 'intent',
        'payload': [
            {'id': id1, 'domain': 'transport', 'intent': 'play'},
            {'id': id2, 'domain': 'transport', 'intent': 'stop'}
        ],
        'source': 'ui'
    }
    
    msg_type, response = protocol.parse_message(json.dumps(intent))
    assert msg_type == 'intent'
    assert response['ack']['ids'] == [id1, id2]
    assert len(response['results']) == 2

def test_bad_json():
    """Test invalid JSON."""
    interpreter = FakeInterpreter()
    protocol = Protocol(interpreter)
    
    msg_type, response = protocol.parse_message('{invalid json')
    assert msg_type is None
    assert response['type'] == 'error'
    assert response['code'] == 'BAD_REQUEST'

def test_unknown_message_type():
    """Test unknown message type."""
    interpreter = FakeInterpreter()
    protocol = Protocol(interpreter)
    
    msg_type, response = protocol.parse_message(json.dumps({'type': 'unknown'}))
    assert msg_type is None
    assert response['type'] == 'error'
    assert response['code'] == 'BAD_REQUEST'

def test_missing_payload():
    """Test intent without payload."""
    interpreter = FakeInterpreter()
    protocol = Protocol(interpreter)
    
    msg_type, response = protocol.parse_message(json.dumps({'type': 'intent'}))
    assert msg_type is None
    assert response['type'] == 'error'
    assert response['code'] == 'BAD_REQUEST'

def test_interpreter_error_handling():
    """Test that interpreter errors don't crash."""
    class FailingInterpreter:
        def execute_batch(self, envelopes):
            raise RuntimeError("Interpreter crashed")
    
    protocol = Protocol(FailingInterpreter())
    intent = {
        'type': 'intent',
        'payload': {'domain': 'test', 'intent': 'test'},
        'source': 'ui'
    }
    
    msg_type, response = protocol.parse_message(json.dumps(intent))
    assert msg_type is None
    assert response['type'] == 'error'
    assert response['code'] == 'INTERNAL_ERROR'

if __name__ == '__main__':
    test_ping_pong()
    test_intent_with_id()
    test_intent_without_id_generates_one()
    test_intent_with_multiple_envelopes()
    test_bad_json()
    test_unknown_message_type()
    test_missing_payload()
    test_interpreter_error_handling()
    print("All tests passed!")
