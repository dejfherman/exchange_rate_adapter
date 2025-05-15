"""
Pydantic I/O models. Allows for pydantic-fueled data validation, makes code more elegant and readable
and provides a few custom tricks with default data formatting.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator, field_serializer
from datetime import datetime, date, timezone
from typing import Literal

MISSING_ID_STR = "<missing_transaction_id>"

class WebsocketMessageType(str, Enum):
    message = "message"
    error = "error"
    heartbeat = "heartbeat"


class InfoMessagePayload(BaseModel):
    marketId: int
    selectionId: int
    odds: float
    stake: float
    currency: str
    received_datetime: datetime = Field(alias="date")

    @field_validator("currency")
    def validate_currency(value: str):
        if not (isinstance(value, str) and len(value) == 3 and value.isupper()):
            raise ValueError("currency must be a 3-letter uppercase string")
        return value

    @property
    def date(self) -> date:
        return self.received_datetime.date()

    @field_serializer('received_datetime')
    def serialize_datetime(self, dt: received_datetime, _info):
        """
        Ensures output format consistent with received request messages whether or not the value is tz-aware.
        Assumes UTC for naive datetimes.
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        return dt.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


class OutgoingPayload(InfoMessagePayload):
    currency: Literal["EUR"] = "EUR"


class WebsocketMessage(BaseModel):
    type: WebsocketMessageType


class HeartbeatMessage(WebsocketMessage):
    type: Literal[WebsocketMessageType.heartbeat] = WebsocketMessageType.heartbeat

    @classmethod
    def json_payload(cls):
        """
        Prevents repeated instantiation and dumping on every heartbeat message.
        """
        if not hasattr(cls, "_payload"):
            cls._payload = cls().model_dump_json()
        return cls._payload


class InfoMessage(WebsocketMessage):
    type: Literal[WebsocketMessageType.message] = WebsocketMessageType.message
    id: int
    payload: InfoMessagePayload


class ErrorMessage(WebsocketMessage):
    type: Literal[WebsocketMessageType.error] = WebsocketMessageType.error
    id: int | Literal["<missing_transaction_id>"] = MISSING_ID_STR
    error_str: str = Field(alias="message")

    @property
    def message(self) -> str:
        return f"Unable to convert stake. Error: {self.error_str}"
