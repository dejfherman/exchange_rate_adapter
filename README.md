# Exchange Rate Conversion Service

## Introduction

The goal was to create an exchange rate conversion service for a theoretical trading platform data pipeline. The service should establish a websocket connection with a remote server from which request messages will come through. Request message format was specified as seen below and there are also heartbeat messages sent from both ends of the websocket connection every second. The service must refresh connection if heartbeat is not received for more than two seconds. Conversion response message must contain the received "stake" value in Euros and a date to which the conversion is relevant.

## Description

The service runs an `asyncio` loop, connecting to a websocket and converting stakes based on WS request messages. Conversion rates used are downloaded from https://freecurrencyapi.com/ service and cached locally in Redis.

## How to run
1. From this (project root) folder activate your python virtual environment of choice.
2. `pip install -r requirements.txt`
3. Have a redis instance available somewhere and set `.env REDIS_URL` to point at it.
4. Get a https://freecurrencyapi.com/ API key and save it in `.env` as `FREECURRENCYAPI_KEY`.
5. Run `python main.py` from project root.


## Message types

The following section provides examples of message formats:

### Heartbeat message

```json
{
    "type": "heartbeat"
}
```

### Currency conversion request message

```json
{
	"type": "message",
	"id": 456,
	"payload": {
		"marketId": 123456,
		"selectionId": 987654,
		"odds": 2.2,
		"stake": 253.67,
		"currency": "USD",
		"date": "2021-05-18T21:32:42.324Z"
	}
}
```

### Currency conversion success response message

```json
{
	"type": "message",
	"id": 456,
	"payload": {
		"marketId": 123456,
		"selectionId": 987654,
		"odds": 2.2,
		"stake": 207.52054,
		"currency": "EUR",
		"date": "2021-05-18T21:32:42.412Z"
	}
}

```

### Currency conversion error response message

```json
{
    "type": "error",
    "id": 456,
    "message": "<error specifications>"
}
```

### Potential further development
- [BUGFIX]: handle when Redis isn't available. Currently it's fatal.
- exception handling code should be abstracted into a separate layer for readability. At the very least into specialized decorators.
- unit tests should be added
- better formatting and some potentially sensitive data concealment for logs
- logging policy and storage would need to be updated based on real traffic. ELK stack or Sentry for viewing would be appropriate.
- alerts to responsible personnel would need to be added to handle unrecoverable exceptions. Potentially some reboot policies. Currently the service intentionally shuts down on some strange errors and will keep trying to reconnect forever on connection drop.
- `startup`, `shutdown` and potentially a few other bash / CLI scripts should be added for cleaner control

### Other, nice-to-have additions
- asynchronous logging. Traffic from the supplied endpoint isn't high, but under more load file writes or other log-writing methods should spawn their own tasks.
- a stronger packaging tool, like `poetry`, should be used.
- stricter validation
- some easy, portable setup for all components of the service as once, for example using `docker-compose`

## Environment Variables

| Variable Name                | Description                                           |
|------------------------------|-------------------------------------------------------|
| `FREECURRENCYAPI_URL`        | Base URL for FreeCurrencyAPI                          |
| `FREECURRENCYAPI_KEY`        | API key for FreeCurrencyAPI                           |
| `REDIS_URL`                  | Redis connection URL                                  |
| `CACHE_TTL_SECONDS`          | Redis cache expiration time in seconds                |
| `REQUESTS_WS_URL`            | WebSocket endpoint for conversion requests            |
| `LOGS_EXCEPTION_FRAMES_LIMIT`| Number of stacktrace frames to log for exceptions     |
| `LOGS_EXPIRATION_DAYS`       | Log file retention period in days (see handler notes) |
| `RETRY_MESSAGE_TTL`          | Max age (seconds) to retry messages after disconnect  |
