import base64
import hashlib
import json
import os
import socket
import struct
import time
from threading import Thread, Lock

try:
    from urllib.parse import urlparse
except ImportError:  # pragma: no cover - python2 fallback
    from urlparse import urlparse

from .Logging import logger


class WebSocketClient(Thread):
    def __init__(self, url, on_message, on_status=None, reconnect_delay=2.0):
        super(WebSocketClient, self).__init__()
        self.daemon = True
        self._url = url
        self._on_message = on_message
        self._on_status = on_status
        self._reconnect_delay = reconnect_delay
        self._socket = None
        self._running = True
        self._send_lock = Lock()

    def stop(self):
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass

    def run(self):
        while self._running:
            try:
                self._connect_and_listen()
            except Exception as exc:
                logger.error(f"WebSocket client error: {exc}")
            if self._running:
                time.sleep(self._reconnect_delay)

    def send_json(self, payload):
        if not self._socket:
            return
        try:
            message = json.dumps(payload)
        except Exception as exc:
            logger.error(f"Failed to encode JSON: {exc}")
            return
        self._send_text(message)

    def _connect_and_listen(self):
        parsed = urlparse(self._url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 80
        path = parsed.path or "/"

        logger.info(f"Connecting to {host}:{port}{path}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))

        websocket_key = base64.b64encode(os.urandom(16)).decode("utf-8")
        headers = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {websocket_key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )

        sock.sendall(headers.encode("utf-8"))
        response = sock.recv(2048).decode("utf-8", errors="ignore")
        if "101" not in response:
            sock.close()
            raise RuntimeError("WebSocket handshake failed")

        self._socket = sock
        if self._on_status:
            self._on_status("connected")

        while self._running:
            message = self._receive_text()
            if message is None:
                break
            try:
                parsed = json.loads(message)
            except Exception as exc:
                logger.error(f"Invalid JSON from server: {exc}")
                continue
            self._on_message(parsed)

        try:
            sock.close()
        except Exception:
            pass
        self._socket = None
        if self._on_status:
            self._on_status("disconnected")

    def _send_text(self, message):
        if not self._socket:
            return
        encoded = message.encode("utf-8")
        length = len(encoded)
        header = bytearray()
        header.append(0x81)

        mask_bit = 0x80
        if length <= 125:
            header.append(mask_bit | length)
        elif length <= 65535:
            header.append(mask_bit | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(mask_bit | 127)
            header.extend(struct.pack("!Q", length))

        masking_key = os.urandom(4)
        masked = bytearray(encoded[i] ^ masking_key[i % 4] for i in range(length))

        with self._send_lock:
            try:
                self._socket.sendall(header + masking_key + masked)
            except Exception as exc:
                logger.error(f"Failed to send WebSocket message: {exc}")

    def _receive_exact(self, size):
        data = b""
        while len(data) < size:
            chunk = self._socket.recv(size - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def _receive_text(self):
        if not self._socket:
            return None
        try:
            header = self._receive_exact(2)
            if not header:
                return None
            byte1, byte2 = struct.unpack("BB", header)
            fin = byte1 & 0x80
            opcode = byte1 & 0x0F
            masked = byte2 & 0x80
            length = byte2 & 0x7F

            if length == 126:
                ext = self._receive_exact(2)
                length = struct.unpack("!H", ext)[0]
            elif length == 127:
                ext = self._receive_exact(8)
                length = struct.unpack("!Q", ext)[0]

            mask_key = None
            if masked:
                mask_key = self._receive_exact(4)

            payload = self._receive_exact(length)
            if payload is None:
                return None

            if masked and mask_key:
                payload = bytes(payload[i] ^ mask_key[i % 4] for i in range(length))

            if opcode == 0x8:
                return None
            if opcode != 0x1:
                return None
            return payload.decode("utf-8", errors="ignore")
        except Exception as exc:
            logger.error(f"Failed to receive WebSocket message: {exc}")
            return None
