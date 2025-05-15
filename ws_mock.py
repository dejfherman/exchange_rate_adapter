"""
This module handles mocks the server side of the assignment websocket connection.
It is not fully developed, but served well during testing.

Usage:
    python ws_mock.py
"""

import asyncio
import signal
import websockets
import json
import random
from datetime import datetime, timedelta, timezone


def random_datetime_within_5_years(iso_string: str) -> str:
    """AI-generated. Yaaaaay..."""

    # Parse the input string to a datetime object
    dt = datetime.strptime(iso_string, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)

    # Calculate total seconds in 5 years (including leap years approx)
    seconds_in_5_years = int(5 * 365.25 * 24 * 60 * 60)

    # Generate random offset: positive or negative
    offset = random.randint(-seconds_in_5_years, seconds_in_5_years)
    new_dt = dt + timedelta(seconds=offset)

    # Format back to ISO 8601 with milliseconds and 'Z'
    # The .%f gives microseconds, we trim to 3 digits for milliseconds
    iso_out = new_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return iso_out


async def handle_client_connection(ws_connection: websockets.ServerConnection):
    path = ws_connection.request.path if hasattr(ws_connection, 'request') else "(unknown)"
    print(f"Client connected to path: {path}")

    async def sender():
        """Periodically sends a conversion request"""
        anchor_datetime_str = "2023-05-18T21:32:42.324Z"

        while True:
            rand_datetime_str = random_datetime_within_5_years(anchor_datetime_str)
            await ws_connection.send(json.dumps({
                "type": "message",
                "id": 730,
                "payload": {
                    "marketId": 123,
                    "selectionId": 456,
                    "odds": 1.5,
                    "stake": 200.0,
                    "currency": "USD",
                    "date": rand_datetime_str
                }
            }))

            print(f"Sent message to {ws_connection.remote_address}")
            await asyncio.sleep(60)

    async def receiver():
        """Echoes received messages to stdout"""

        try:
            async for message in ws_connection:
                if json.loads(message)["type"] == "heartbeat":
                    continue
                print(f"Received: {message}")
        except websockets.exceptions.ConnectionClosed:
            print("Client disconnected")

    await asyncio.gather(sender(), receiver())
    print("Connection closed cleanly")


async def main():
    """
    Main event loop of a mock websocket server used for development and testing. Runs tasks defined
    in handle_client_connection.

    Doesn't do heartbeat.

    Supposed to shut down gracefully on SIGINT, but would need more work for that.
    """
    stop_event = asyncio.Event()

    def shutdown():
        print(f"Shutdown called")
        stop_event.set()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, shutdown)

    async with websockets.serve(handle_client_connection, "localhost", 8765):
        print("Mock WebSocket server running at ws://localhost:8765")
        await stop_event.wait()
        print("Shutting down")

if __name__ == "__main__":
    asyncio.run(main())
