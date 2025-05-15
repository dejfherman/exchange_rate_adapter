"""
Handles periodic heartbeat websocket messages
"""

import asyncio
import time
from websockets import ClientConnection
from app.models import HeartbeatMessage
from app.logger import AppLogger as log

class HeartbeatTimeout(ConnectionError):
    pass

class HeartbeatManager:
    def __init__(self, ws: ClientConnection):
        self.ws = ws
        self.last_received = time.time()
        self._stop_event = asyncio.Event()

    async def run(self):
        """
        Sends a heartbeat every second. Also closes connection if 2 seconds pass without having received one.
        """
        try:
            while not self._stop_event.is_set():
                await self.ws.send(HeartbeatMessage.json_payload())
                await asyncio.sleep(1)
                if time.time() - self.last_received > 2:
                    # Exceeded allowed heartbeat loss window; close connection.
                    raise HeartbeatTimeout("No heartbeat received in >2 seconds")
        except ConnectionError as e:
            err_msg = "Heartbeat timeout"
            if not isinstance(e, HeartbeatTimeout):
                log.exception(exc=e, tag=__name__)
                err_msg = "Unexpected heartbeat connection error"

            self.stop()
            log.warning(msg=f"{err_msg}, closing connection", tag=__name__)
            try:
                await self.ws.close()
            except Exception:
                # It's possible the connection is already closed; log and continue
                log.warning(msg="Error during ws.close()", tag=__name__)
        finally:
            self.stop()

    def mark_received(self):
        """
        Call this when a heartbeat message is received.
        """
        self.last_received = time.time()

    def stop(self):
        self._stop_event.set()
