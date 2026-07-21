"""Entrypoint: python -m kungfu_chess.gui.network.network_gui_main

Phase F Milestone 1's graphical networked client - drives the same
permanent CLI login flow as server/reference_client.py (via
server.login_client.perform_login), then offers the same choice
reference_client.py does between the unrated quick_local game and
Phase C's rated "play" matchmaking queue, before handing off to
network_game_loop.run() for the actual graphical board. Real I/O
throughout - excluded from coverage, verified by running it, not by
unit tests (same treatment as gui/gui_main.py and
server/reference_client.py).
"""
import asyncio
import sys

import websockets  # pragma: no cover

from kungfu_chess.gui.network import network_game_loop  # pragma: no cover
from kungfu_chess.server import schemas  # pragma: no cover
from kungfu_chess.server.login_client import perform_login  # pragma: no cover

SERVER_URL = "ws://localhost:8765"  # pragma: no cover


async def main():  # pragma: no cover
    async with websockets.connect(SERVER_URL) as websocket:
        flow = await perform_login(websocket)
        if flow is None:
            return

        mode = input("[Q]uick local or ranked [p]lay? [Q/p]: ").strip().lower()
        if mode.startswith("p"):
            await websocket.send(schemas.encode(schemas.make_envelope("play", {})))
            print(f"Logged in as {flow.username}. Searching for a ranked match...")
        else:
            await websocket.send(schemas.encode(schemas.make_envelope(
                "join_game", {"mode": "quick_local"})))
            print(f"Logged in as {flow.username}. Waiting for an opponent...")

        try:
            await network_game_loop.run(websocket, flow.username)
        except (websockets.exceptions.ConnectionClosed, KeyboardInterrupt):
            pass


if __name__ == "__main__":  # pragma: no cover
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
