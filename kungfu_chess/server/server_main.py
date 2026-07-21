"""Composition root: wires GameService, ApplicationMessageBus and
WebSocketGateway, runs the periodic hybrid-tick loop (Part 10), and starts
the WebSocket server. Real I/O throughout - excluded from coverage, same
treatment as gui/game_loop.py and BoardParser._read_stdin. Verified by the
manual end-to-end walkthrough in the architecture plan's Part 15, not by
unit tests.
"""
import asyncio
import logging

import websockets  # pragma: no cover

from kungfu_chess.messaging.application_message_bus import ApplicationMessageBus  # pragma: no cover
from kungfu_chess.application.auth_service import create_sqlite_backed_service  # pragma: no cover
from kungfu_chess.application.game_service import GameService  # pragma: no cover
from kungfu_chess.server.websocket_gateway import WebSocketGateway  # pragma: no cover

HOST = "localhost"  # pragma: no cover
PORT = 8765  # pragma: no cover
TICK_INTERVAL_MS = 75  # pragma: no cover
DB_PATH = "kungfu_chess.db"  # pragma: no cover


async def _tick_loop(game_service, gateway, tick_interval_ms=TICK_INTERVAL_MS):  # pragma: no cover
    """Hybrid time advancement: only ticks sessions that currently report
    pending motion/airborne/cooldown activity (GameSession.has_pending_
    activity) - a session with nothing in flight costs nothing here, but
    an in-flight Motion or an expiring cooldown still resolves and
    broadcasts without needing a new client command. Each active tick is
    followed by a render_state broadcast (Phase F Milestone 1) so any
    connected networked GUI client can animate the in-between motion,
    not just the discrete before/after board states."""
    while True:
        await asyncio.sleep(tick_interval_ms / 1000)
        for game_id, session in game_service.sessions().items():
            if session.has_pending_activity():
                await game_service.tick(game_id, tick_interval_ms)
                await gateway.broadcast_render_state(game_id, session)


async def run(host=HOST, port=PORT, db_path=DB_PATH):  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    message_bus = ApplicationMessageBus()
    game_service = GameService(message_bus)
    auth_service = create_sqlite_backed_service(db_path)
    gateway = WebSocketGateway(game_service, message_bus, auth_service=auth_service)

    tick_task = asyncio.create_task(_tick_loop(game_service, gateway))
    try:
        async with websockets.serve(gateway.handle_connection, host, port):
            logger.info("Kung Fu Chess server listening on ws://%s:%s", host, port)
            await asyncio.Future()  # run until cancelled (Ctrl+C)
    finally:
        tick_task.cancel()


def main():  # pragma: no cover
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
