import queue
from .Logging import logger


class DispatchQueue:
    def __init__(self):
        self._queue = queue.Queue()

    def put(self, message):
        self._queue.put(message)

    def drain(self, handler):
        processed = 0
        while not self._queue.empty():
            message = self._queue.get()
            try:
                handler(message)
            except Exception as exc:
                logger.error(f"Dispatch handler error: {exc}")
            processed += 1
        return processed
