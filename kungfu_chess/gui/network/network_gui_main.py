"""Entrypoint: python -m kungfu_chess.gui.network.network_gui_main

Phase F Milestone 1's graphical networked client - covers every join
path server/reference_client.py already does: the permanent CLI login
flow (server.login_client.perform_login), then a choice between the
unrated quick_local game, Phase C's rated "play" queue, and Phase E's
rooms (create one and wait, or join one - as the second player or a
read-only spectator, decided by the server, not the client), before
handing off to network_game_loop.run() for the actual graphical board.
Real I/O throughout - excluded from coverage, verified by running it,
not by unit tests (same treatment as gui/gui_main.py and
server/reference_client.py).

Phase D (Decision 7): mirrors reference_client.py's automatic
reconnect - if the connection drops mid-game, a fresh connection is
opened and "reconnect" sent with the session token already held in
memory (no re-login), resuming network_game_loop.run() via its
`resume` parameter rather than repeating the join handshake.
"""
import asyncio
import json
import sys

import websockets  # pragma: no cover

from kungfu_chess.gui.network import network_game_loop  # pragma: no cover
from kungfu_chess.server import protocol, schemas  # pragma: no cover
from kungfu_chess.server.login_client import perform_login  # pragma: no cover
from kungfu_chess.server.network_config import SERVER_URL  # pragma: no cover


async def _attempt_reconnect(websocket, session_token):  # pragma: no cover
    await websocket.send(schemas.encode(schemas.make_envelope(
        protocol.RECONNECT, {"session_token": session_token})))
    response = json.loads(await websocket.recv())
    if response["type"] == protocol.ERROR:
        print(f"Reconnect failed: {response['payload']['code']}")
        return None
    print("Reconnected.")
    return response["game_id"], response["payload"]["board"]


async def _choose_and_join(websocket, my_username):  # pragma: no cover
    """Prompts for quick_local / ranked play / room create / room join,
    sends the matching wire message(s), and returns (game_id, board_rows,
    my_color) once the join is fully resolved - or (None, None, None)
    if nothing could be joined."""
    mode = input(
        "[Q]uick local, ranked [p]lay, [c]reate a room, or [j]oin a room? [Q/p/c/j]: "
    ).strip().lower()

    if mode.startswith("p"):
        await websocket.send(schemas.encode(schemas.make_envelope(protocol.PLAY, {})))
        print(f"Logged in as {my_username}. Searching for a ranked match...")
        return await network_game_loop.await_fresh_game_start(websocket, my_username)

    if mode.startswith("c"):
        await websocket.send(schemas.encode(schemas.make_envelope(protocol.CREATE_ROOM, {})))
        created = json.loads(await websocket.recv())
        room_id = created["payload"]["room_id"]
        print(f"Room created: {room_id}. Share this code - waiting for an opponent...")
        return await network_game_loop.await_fresh_game_start(websocket, my_username)

    if mode.startswith("j"):
        room_id = input("Room code: ").strip().upper()
        return await network_game_loop.join_game_as_room(websocket, room_id, my_username)

    await websocket.send(schemas.encode(schemas.make_envelope(
        protocol.JOIN_GAME, {"mode": "quick_local"})))
    print(f"Logged in as {my_username}. Waiting for an opponent...")
    return await network_game_loop.await_fresh_game_start(websocket, my_username)


async def main():  # pragma: no cover
    session_token = None
    my_username = None
    my_color = None  # learned once, preserved across a later reconnect

    while True:
        try:
            async with websockets.connect(SERVER_URL) as websocket:
                if session_token is not None:
                    result = await _attempt_reconnect(websocket, session_token)
                    if result is None:
                        return
                    game_id, board_rows = result
                else:
                    flow = await perform_login(websocket)
                    if flow is None:
                        return
                    session_token = flow.session_token
                    my_username = flow.username

                    game_id, board_rows, my_color = await _choose_and_join(websocket, my_username)
                    if board_rows is None:
                        return

                await network_game_loop.run(
                    websocket, my_username, resume=(game_id, board_rows, my_color))
                return  # the render loop ended cleanly (ESC, game over) - done
        except websockets.exceptions.ConnectionClosed:
            if session_token is None:
                return
            print("Connection lost - attempting to reconnect...")
            continue
        except KeyboardInterrupt:
            return


if __name__ == "__main__":  # pragma: no cover
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
