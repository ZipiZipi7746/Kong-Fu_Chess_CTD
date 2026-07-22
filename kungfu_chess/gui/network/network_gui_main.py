"""Entrypoint: python -m kungfu_chess.gui.network.network_gui_main

Phase F Milestone 2: replaces every console input()-driven prompt
(login, mode selection, room code entry, waiting status) with real
graphical screens rendered in the same cv2 window the board itself
uses - a Home/Login screen, a Menu screen (quick_local / ranked play /
create room / join room, with the player's username and Elo rating
shown), and a Waiting screen (status text + Cancel), before handing
off to network_game_loop.run() for the actual graphical board. See
gui/network/screens.py (click/keyboard logic) and
gui/network/screen_rendering.py (pure draw layout) for the reusable
pieces; gui/network/screen_loop.py is the real I/O (cv2 window, mouse,
keyboard) that drives them.

Covers every join path server/reference_client.py's text version does:
quick_local, ranked play, and Phase E rooms (create/join, as the second
player or a read-only spectator - decided by the server, never the
client). Real I/O throughout - excluded from coverage, verified by
running it, not by unit tests (same treatment as gui/gui_main.py and
server/reference_client.py).

Phase D (Decision 7): mirrors reference_client.py's automatic
reconnect - if the connection drops mid-game, a fresh connection is
opened and "reconnect" sent with the session token already held in
memory (no re-login), resuming network_game_loop.run() via its
`resume` parameter rather than repeating the join screens. Reconnection
itself is not yet graphical (console status prints only) - a fast-
follow, not part of this pass's Home/Login/Menu screen scope.
"""
import asyncio
import json
import sys

import websockets  # pragma: no cover

from kungfu_chess.gui.network import network_game_loop, screen_loop, screen_rendering  # pragma: no cover
from kungfu_chess.gui.network.screens import LoginScreen, MenuScreen, WaitingScreen  # pragma: no cover
from kungfu_chess.server import protocol, schemas  # pragma: no cover
from kungfu_chess.server.network_config import SERVER_URL  # pragma: no cover


async def _do_login(websocket):  # pragma: no cover
    """Runs the graphical login screen until register+login succeeds or
    the window is closed. Returns (username, session_token, rating), or
    None if the user closed the window."""
    screen = LoginScreen(screen_loop.CONTENT_W, screen_loop.CONTENT_H)
    while True:
        action = await screen_loop.run_screen(screen, screen_rendering.render_login_screen)
        if action is None:
            return None

        username = screen.username_field.text
        password = screen.password_field.text

        if screen.is_new_account:
            await websocket.send(schemas.encode(schemas.make_envelope(
                protocol.REGISTER, {"username": username, "password": password})))
            response = json.loads(await websocket.recv())
            if response["type"] == protocol.ERROR:
                screen.error_message = f"Registration failed: {response['payload']['code']}"
                continue

        await websocket.send(schemas.encode(schemas.make_envelope(
            protocol.LOGIN, {"username": username, "password": password})))
        response = json.loads(await websocket.recv())
        if response["type"] == protocol.ERROR:
            screen.error_message = f"Login failed: {response['payload']['code']}"
            screen.password_field.clear()
            continue

        payload = response["payload"]
        return payload["username"], payload["session_token"], payload["rating"]


async def _do_wait(network_coro, status_text):  # pragma: no cover
    """Runs `network_coro` as a background task while showing a Waiting
    screen with `status_text`. Returns ("completed", (game_id,
    board_rows, my_color)) or ("cancelled", None)."""
    screen = WaitingScreen(screen_loop.CONTENT_W, screen_loop.CONTENT_H, status_text)
    task = asyncio.create_task(network_coro)
    return await screen_loop.run_waiting_screen(screen, task)


async def _choose_and_join(websocket, my_username, my_rating):  # pragma: no cover
    """Runs the graphical menu screen and whichever follow-up wait is
    needed, returning (game_id, board_rows, my_color) once a game
    actually starts - or (None, None, None) if the window was closed."""
    while True:
        menu_screen = MenuScreen(screen_loop.CONTENT_W, screen_loop.CONTENT_H)
        action = await screen_loop.run_screen(
            menu_screen, screen_rendering.render_menu_screen, my_username, my_rating)
        if action is None:
            return None, None, None

        if action == "quick_local":
            await websocket.send(schemas.encode(schemas.make_envelope(
                protocol.JOIN_GAME, {"mode": "quick_local"})))
            status, result = await _do_wait(
                network_game_loop.await_fresh_game_start(websocket, my_username),
                "Waiting for an opponent...")

        elif action == "ranked_play":
            await websocket.send(schemas.encode(schemas.make_envelope(protocol.PLAY, {})))
            status, result = await _do_wait(
                network_game_loop.await_fresh_game_start(websocket, my_username),
                "Searching for a ranked match...")
            if status == "cancelled":
                await websocket.send(schemas.encode(schemas.make_envelope(
                    protocol.CANCEL_MATCHMAKING, {})))

        elif action == "create_room":
            await websocket.send(schemas.encode(schemas.make_envelope(protocol.CREATE_ROOM, {})))
            created = json.loads(await websocket.recv())
            room_id = created["payload"]["room_id"]
            status, result = await _do_wait(
                network_game_loop.await_fresh_game_start(websocket, my_username),
                f"Room created: {room_id} - waiting for an opponent...")

        else:  # "join_room"
            room_id = menu_screen.room_code_field.text.strip().upper()
            status, result = await _do_wait(
                network_game_loop.join_game_as_room(websocket, room_id, my_username),
                f"Joining room {room_id}...")

        if status == "completed" and result[1] is not None:
            return result
        # cancelled, timed out, or rejected - back to the menu screen


async def _attempt_reconnect(websocket, session_token):  # pragma: no cover
    await websocket.send(schemas.encode(schemas.make_envelope(
        protocol.RECONNECT, {"session_token": session_token})))
    response = json.loads(await websocket.recv())
    if response["type"] == protocol.ERROR:
        print(f"Reconnect failed: {response['payload']['code']}")
        return None
    print("Reconnected.")
    return response["game_id"], response["payload"]["board"]


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
                    login_result = await _do_login(websocket)
                    if login_result is None:
                        return
                    my_username, session_token, my_rating = login_result

                    game_id, board_rows, my_color = await _choose_and_join(
                        websocket, my_username, my_rating)
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
