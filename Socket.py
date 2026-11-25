import socket
import hashlib
import base64
from threading import Thread, Lock
import struct
import json

try:
    from .Logging import logger
except ImportError:
    import logging
    logger = logging.getLogger("mantra")

try:
    from .port_range import start_port, end_port
except ImportError:
    start_port = 39031
    end_port = 39038

ALLOWED_ORIGINS = (None, 'localhost', '127.0.0.1')

class Socket(Thread):
    def __init__(self, c_instance, on_message_callback):
        Thread.__init__(self)
        self._c_instance = c_instance
        self._on_message_callback = on_message_callback
        self.socket = None
        self.connection = None
        self._send_lock = Lock()
        self.daemon = True

    def run(self):
        try:
            self.create_socket(start_port, end_port)
        except Exception as e:
            logger.error(f'Error creating socket: {e}')

    def create_socket(self, start_port, end_port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        for port in range(start_port, end_port + 1):
            try:
                self.socket.bind(('', port))
                logger.info(f"Server started on port {port}, waiting for connections...")
                break
            except socket.error as e:
                logger.warning(f"Port {port} is unavailable: {e}")
                if port == end_port:
                    logger.error("No available ports in the specified range.")
                    return

        self.socket.listen(1)
        while True:
            try:
                connection, _ = self.socket.accept()
                if connection:
                    logger.info("Client connected")
                    self.connection = connection
                    Thread(target=self.handle_connection, args=[connection]).start()
            except Exception as e:
                logger.error(f'Error accepting connection: {e}')

    def handle_connection(self, connection):
        try:
            if self.perform_handshake(connection):
                while True:
                    msg = self.receive_message(connection)
                    if msg is None:
                        break
                    if msg == 'ping':
                        self.send_message(json.dumps({'type': 'pong'}))
                    else:
                        logger.info(f'Received message: {msg}')
                        self._on_message_callback(msg)
        except Exception as e:
            logger.error(f'Connection error: {e}')
        finally:
            self.disconnect()

    def perform_handshake(self, connection):
        try:
            logger.info("Performing handshake...")
            request = connection.recv(1024).decode('utf-8')
            logger.info(f"Handshake request: {request}")

            headers = self.parse_headers(request)
            origin = headers.get('Origin')
            if origin:
                origin_host = origin.replace('http://', '').replace('https://', '').split(':')[0]
                if origin_host not in ALLOWED_ORIGINS:
                    logger.warning(f"Origin not allowed: {origin}")
                    return False

            websocket_key = headers.get('Sec-WebSocket-Key')
            if not websocket_key:
                logger.error('Missing Sec-WebSocket-Key')
                return False

            websocket_accept = self.generate_accept_key(websocket_key)

            response = (
                'HTTP/1.1 101 Switching Protocols\r\n'
                'Upgrade: websocket\r\n'
                'Connection: Upgrade\r\n'
                f'Sec-WebSocket-Accept: {websocket_accept}\r\n\r\n'
            )

            connection.send(response.encode('utf-8'))
            logger.info("Handshake response sent")
            return True
        except Exception as e:
            logger.error(f'Handshake error: {e}')
            return False

    def parse_headers(self, request):
        headers = {}
        lines = request.split('\r\n')
        for line in lines[1:]:
            if line:
                try:
                    key, value = line.split(': ', 1)
                    headers[key] = value
                except ValueError:
                    pass
        return headers

    def generate_accept_key(self, websocket_key):
        magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        return base64.b64encode(
            hashlib.sha1((websocket_key + magic_string).encode()).digest()
        ).decode('utf-8')

    def receive_message(self, connection):
        try:
            complete_message = bytearray()
            while True:
                frame_header = connection.recv(2)
                if len(frame_header) < 2:
                    return None

                byte1, byte2 = struct.unpack('BB', frame_header)
                fin = byte1 & 0b10000000
                opcode = byte1 & 0b00001111
                masked = byte2 & 0b10000000
                payload_length = byte2 & 0b01111111

                if masked != 0b10000000:
                    logger.info('Client data must be masked')
                    return None

                if payload_length == 126:
                    extended_payload_length = connection.recv(2)
                    payload_length = int.from_bytes(extended_payload_length, byteorder='big')
                elif payload_length == 127:
                    extended_payload_length = connection.recv(8)
                    payload_length = int.from_bytes(extended_payload_length, byteorder='big')

                masking_key = connection.recv(4)
                payload_data = bytearray()
                remaining = payload_length
                while remaining > 0:
                    chunk = connection.recv(min(remaining, 1024))
                    if not chunk:
                        return None
                    payload_data.extend(chunk)
                    remaining -= len(chunk)

                decoded_bytes = bytearray()
                for i in range(len(payload_data)):
                    decoded_bytes.append(payload_data[i] ^ masking_key[i % 4])

                complete_message.extend(decoded_bytes)

                if fin:
                    break

            if opcode == 0x1:
                return complete_message.decode('utf-8')
            elif opcode == 0x8:
                logger.info('Connection closed by client')
                return None
            elif opcode == 0x9:
                self.send_message(json.dumps({'type': 'pong'}))
                return self.receive_message(connection)
            else:
                logger.info(f'Unsupported frame type: {opcode}')
                return None
        except Exception as e:
            logger.error(f'Error receiving message: {e}')
            return None

    def send_message(self, message):
        with self._send_lock:
            try:
                if self.connection and isinstance(message, str):
                    msg_bytes = message.encode('utf-8')
                    frame = bytearray()
                    fin = 0b10000000
                    frame.append(fin | 0x1)

                    length = len(msg_bytes)
                    if length <= 125:
                        frame.append(length)
                    elif length <= 65535:
                        frame.append(126)
                        frame.extend(struct.pack('!H', length))
                    else:
                        frame.append(127)
                        frame.extend(struct.pack('!Q', length))

                    frame.extend(msg_bytes)
                    self.connection.sendall(bytes(frame))
                else:
                    logger.info("Connection closed or invalid message")
            except Exception as e:
                logger.error(f'Error sending message: {e}')

    def disconnect(self):
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
        except Exception as e:
            logger.error(f'Error closing connection: {e}')
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
        except Exception as e:
            logger.error(f'Error closing socket: {e}')
