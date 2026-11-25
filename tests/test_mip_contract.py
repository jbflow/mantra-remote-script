"""MIP v0.3 contract: every transport, structure and parameters example is sent over the WebSocket, and the
result statuses and the Live mock session are checked against what the example asks for.

The script side is the real Socket and Protocol, running handlers.execute_batch against the mock. Mantra itself
needs Ableton's ControlSurface, so _Script.on_message mirrors Mantra._handle_message.
"""
import base64
import json
import os
import socket
import struct
import time
from pathlib import Path

import pytest

Live = pytest.importorskip("Live")

import Socket as script_socket  # noqa: E402
from Protocol import Protocol  # noqa: E402
from handlers import execute_batch  # noqa: E402

EXAMPLES = Path(__file__).resolve().parents[2] / 'musical-intent-protocol' / 'examples'
DOMAINS = {'transport', 'structure', 'parameters'}


# ------------------------------------------------------------------ examples and their expectations

def _domains(example):
    intents = example if isinstance(example, list) else [example]
    return {item['domain'] for item in intents}


def _example_names():
    return [path.name for path in sorted(EXAMPLES.glob('*.json'))
            if _domains(json.loads(path.read_text())) & DOMAINS]


def _track(song, name, midi=True):
    track = song.create_midi_track() if midi else song.create_audio_track()
    track.name = name
    return track


def _nothing(song, add_parameter):
    pass


def _signature_3_4(song, add_parameter):
    song.signature_numerator = 3


def _drums(song, add_parameter):
    _track(song, 'Drums')


def _bass(song, add_parameter):
    _track(song, 'Bass')


def _keep_and_scratch(song, add_parameter):
    _track(song, 'Keep')
    _track(song, 'Scratch Pad')


def _pad_with_eq(song, add_parameter):
    add_parameter(_track(song, 'Pad').insert_device('EQ Eight'), 'Frequency', 20.0, 22050.0, 1000.0)


def _bass_with_compressor(song, add_parameter):
    add_parameter(_track(song, 'Bass').insert_device('Compressor'), 'Attack', 0.0, 120.0, 10.0)


def _lead_vocal(song, add_parameter):
    _track(song, 'Lead Vocal')


def _playing(song):
    assert song.is_playing


def _tempo_128(song):
    assert song.tempo == 128.0


def _signature_4_4(song):
    assert (song.signature_numerator, song.signature_denominator) == (4, 4)


def _drums_created(song):
    assert [t.name for t in song.tracks] == ['Drums'] and song.tracks[0].has_audio_input


def _bass_duplicated(song):
    assert [t.name for t in song.tracks] == ['Bass', 'Bass Double']


def _scratch_removed(song):
    assert [t.name for t in song.tracks] == ['Keep']


def _renamed_beats(song):
    assert [t.name for t in song.tracks] == ['Beats']


def _frequency_decreased(song):
    assert song.tracks[0].devices[0].parameters[1].display_value == 800.0


def _attack_increased(song):
    assert song.tracks[0].devices[0].parameters[1].display_value == 15.0


def _volume_set(song):
    assert song.tracks[0].mixer_device.volume.display_value == -6.0


# (setup, check, expected result statuses in order)
CONTRACT = {
    'transport.play.json': (_nothing, _playing, ['ok']),
    'transport.set_tempo.json': (_nothing, _tempo_128, ['ok']),
    'transport.set_time_signature.json': (_signature_3_4, _signature_4_4, ['ok']),
    'structure.create_track.json': (_nothing, _drums_created, ['ok']),
    'structure.duplicate_track.json': (_bass, _bass_duplicated, ['ok']),
    'structure.remove_track.json': (_keep_and_scratch, _scratch_removed, ['ok']),
    'structure.rename_track.json': (_drums, _renamed_beats, ['ok']),
    'parameters.decrease_frequency.json': (_pad_with_eq, _frequency_decreased, ['ok']),
    'parameters.increase_attack.json': (_bass_with_compressor, _attack_increased, ['ok']),
    'parameters.set_volume.json': (_lead_vocal, _volume_set, ['ok']),
    # The music and timbre intents are not in this release; they must be reported, not dropped.
    'multi_intent.example.json': (_nothing, _playing, ['ok', 'error', 'error']),
}


# ------------------------------------------------------------------ WebSocket plumbing

class _Script:
    """Socket callback: runs each message through Protocol and sends back the frames Mantra sends."""

    def __init__(self):
        self.protocol = Protocol(self)
        self.socket = None

    def execute_batch(self, envelopes):
        app = Live.Application.get_application()
        return execute_batch(envelopes, app.get_document(), app)

    def on_message(self, text):
        kind, response = self.protocol.parse_message(text)
        if kind == 'intent':
            self.socket.send_message(json.dumps(response['ack']))
            for result in response['results']:
                self.socket.send_message(json.dumps({'type': 'result', **result}))
        else:
            self.socket.send_message(json.dumps(response))


class _Client:
    """A minimal WebSocket client: masked text frames out, unmasked frames back."""

    def __init__(self, port):
        self.sock = self._connect(port)
        key = base64.b64encode(os.urandom(16)).decode('ascii')
        self.sock.sendall(('GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\n'
                           'Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n'
                           % key).encode('ascii'))
        response = b''
        while b'\r\n\r\n' not in response:
            response += self.sock.recv(1024)
        assert b' 101 ' in response.split(b'\r\n')[0]

    @staticmethod
    def _connect(port):
        deadline = time.time() + 5
        while True:
            try:
                return socket.create_connection(('127.0.0.1', port), timeout=5)
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(0.05)

    def send_json(self, message):
        payload = json.dumps(message).encode('utf-8')
        mask = os.urandom(4)
        if len(payload) <= 125:
            header = bytes([0x81, 0x80 | len(payload)])
        else:
            header = bytes([0x81, 0x80 | 126]) + struct.pack('!H', len(payload))
        masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def recv_json(self):
        length = self._recv_exact(2)[1] & 0x7F
        if length == 126:
            length = struct.unpack('!H', self._recv_exact(2))[0]
        return json.loads(self._recv_exact(length).decode('utf-8'))

    def intent(self, payload):
        """Sends one intent and returns (ack, results) as the script answered them."""
        self.send_json({'type': 'intent', 'payload': payload})
        ack = self.recv_json()
        results = [self.recv_json() for _ in ack['ids']]
        assert all(result['type'] == 'result' for result in results)
        return ack, results

    def _recv_exact(self, count):
        data = b''
        while len(data) < count:
            chunk = self.sock.recv(count - len(data))
            if not chunk:
                raise ConnectionError('script closed the connection')
            data += chunk
        return data

    def close(self):
        self.sock.close()


@pytest.fixture(scope='module')
def script_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(script_socket, 'start_port', port)
        patch.setattr(script_socket, 'end_port', port)
        script = _Script()
        server = script_socket.Socket(None, script.on_message)
        script.socket = server
        server.start()
        yield port


_KEEP_OPEN = []  # Socket.disconnect() also closes the listening socket, and its accept loop then spins logging errors.


@pytest.fixture(scope='module')
def client(script_port):
    # One connection serves the module, and it stays referenced so it only closes when the process exits.
    connection = _Client(script_port)
    _KEEP_OPEN.append(connection)
    return connection


# ------------------------------------------------------------------ tests

def test_every_contract_example_has_a_setup_and_a_check():
    assert set(_example_names()) == set(CONTRACT)


@pytest.mark.parametrize('name', _example_names())
def test_example_round_trips_over_the_websocket(name, client, song, add_parameter, shown_in_units):
    setup, check, statuses = CONTRACT[name]
    setup(song, add_parameter)
    ack, results = client.intent(json.loads((EXAMPLES / name).read_text()))
    assert ack['status'] == 'accepted'
    assert [result['id'] for result in results] == ack['ids']
    assert [result['status'] for result in results] == statuses
    check(song)
