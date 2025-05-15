import asyncio
from app.logger import AppLogger
from app.ws_client import run_ws_client

if __name__ == "__main__":
    AppLogger.setup()
    AppLogger.info("Starting app")
    asyncio.run(run_ws_client())
