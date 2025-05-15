"""
Main logic module. Runs the event loop, spawns and manages processing tasks, receives and sends websocket messages.
Also happens to contain most of the exception handling and logging.
"""

import asyncio
import websockets
import json
import traceback
from httpx import HTTPStatusError
from pydantic import ValidationError
from time import time
from app.models import InfoMessage, OutgoingPayload, ErrorMessage, HeartbeatMessage, MISSING_ID_STR
from app.rate_provider import get_freecurrencyapi_rate, ConversionDataException
from app.heartbeat import HeartbeatManager
from app.config import settings
from app.logger import AppLogger as log

# task buffer for message retries in case of connection loss
pending_replies = asyncio.Queue()


async def process_message(msg_str: str, ws: websockets.ClientConnection):
    """
    Parses a received msg_str, converts stake value to EUR and sends a response message via the WS connection.
    Logs the received message.
    """
    # validate input
    try:
        msg = InfoMessage.model_validate_json(msg_str)
    except ValidationError as e:
        log.exception(exc=e, tag=__name__)
        await send_error_response(
            connection=ws,
            raw_msg=msg_str,
            err_msg=f"Input validation issues - {"; ".join(error["msg"] for error in e.errors())}",
        )
        return

    try:
        log.info(msg=f"Processing transaction ID {msg.id}", tag=__name__)
        # fetch conversion rate and convert stake
        rate_inverse = await get_freecurrencyapi_rate(msg.payload.currency, msg.payload.date)
        converted_stake = round(msg.payload.stake / rate_inverse, 5)

        # create response message and send
        response_payload = OutgoingPayload(
            **msg.payload.model_dump(exclude=["currency", "received_datetime", "stake"]),
            stake=converted_stake,
            currency="EUR",
            date=msg.payload.date
        )
        response = InfoMessage(
            id=msg.id,
            payload=response_payload,
        )
        response_str = response.model_dump_json(by_alias=True)

        log.info(msg=f"Sending response: \n{response_str}", tag=__name__)
        await ws.send(response_str)

    except websockets.ConnectionClosed:
        # TODO: should be wrapped around the whole function
        log.warning(
            msg=f"Connection closed while sending reply to transaction ID {msg.id}. Scheduling task for a retry.",
            tag=__name__
        )
        await pending_replies.put(msg_str, time())
    except (HTTPStatusError, ConversionDataException) as e:
        message_str = "Remote API exception."
        log.exception(exc=e, msg=message_str, tag=__name__)
        if isinstance(e, ConversionDataException):
            message_str = f"{message_str} {e}"
        await send_error_response(
            connection=ws,
            raw_msg=msg_str,
            err_msg=message_str,
        )
    except (ValueError, ValidationError) as e:
        log.exception(exc=e, tag=__name__)
        await send_error_response(
            connection=ws,
            raw_msg=msg_str,
            err_msg="Unexpected internal service error."
        )
    except Exception as e:
        # anything that gets here is likely to keep happening if service continues running
        # this will be raised higher and logged during shutdown
        await send_error_response(
            connection=ws,
            raw_msg=msg_str,
            err_msg="Fatal internal service error. Shutting down."
        )
        raise e


async def send_error_response(connection: websockets.ClientConnection, raw_msg: str, err_msg: str):
    """
    Sends an error message via (ws) connection. Logs the message.
    """
    try:
        transaction_id = json.loads(raw_msg).get("id")
    except json.decoder.JSONDecodeError:
        err_msg = "Message could not be decoded as JSON"

    try:
        transaction_id = int(transaction_id)
    except (ValueError, UnboundLocalError):
        transaction_id = MISSING_ID_STR

    err = ErrorMessage(id=transaction_id, message=err_msg)
    err_str = err.model_dump_json(by_alias=True)

    log.info(msg=f"Sending response: \n{err_str}", tag=__name__)
    await connection.send(err_str)


async def retry_pending_messages(ws):
    """
    Reschedule pending messages for processing after reconnect. Anything older than RETRY_MESSAGE_TTL is dropped.
    """
    while not pending_replies.empty():
        msg, timestamp = await pending_replies.get()

        if time() - timestamp > settings.RETRY_MESSAGE_TTL:
            continue

        asyncio.create_task(process_message(msg, ws))
        # give other tasks a chance to run in case of a large pending queue
        await asyncio.sleep(0)


async def handle_messages(ws: websockets.ClientConnection, hb: HeartbeatManager):
    """
    Accepts messages, marks heartbeats and schedules other message types for processing.
    """
    async for msg_str in ws:
        try:
            HeartbeatMessage.model_validate_json(msg_str)
        except ValidationError:
            # process as info message if not valid heartbeat
            log.info(msg=f"Received message:\n{msg_str}", tag=__name__)
            asyncio.create_task(process_message(msg_str, ws))
        else:
            hb.mark_received()


async def run_ws_client():
    """
    Main event loop
    """
    while True:
        try:
            async with websockets.connect(settings.REQUESTS_WS_URL) as ws:
                log.info(msg="WS connection established", tag=__name__)
                hb = HeartbeatManager(ws)
                hb_task = asyncio.create_task(hb.run())
                msg_task = asyncio.create_task(handle_messages(ws, hb))

                # tasks complete on error or disconnect, wait only for the first
                done, pending = await asyncio.wait(
                    [hb_task, msg_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)

                # retry pending reply tasks after reconnect
                await retry_pending_messages(ws)

        except (websockets.WebSocketException, OSError) as e:
            log.exception(exc=e, tag=__name__)
            log.info(msg=f"WebSocket error: {e}. Reconnecting in 2s.", tag=__name__)

            print(f"WebSocket error: {e}. Reconnecting in 2s.")
            await asyncio.sleep(2)
        except Exception as e:
            # anything that gets here is likely fatal and will keep happening, so shutdown is appropriate
            log.exception(exc=e, tag=__name__)
            log.info(msg=f"Unexpected error: {e}. Shutting down.", tag=__name__)

            print(f"Unexpected error: {e}. Shutting down.")
            traceback.print_exc()
            break
