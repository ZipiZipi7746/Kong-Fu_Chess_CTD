"""Throwaway reference client - validates the WebSocket protocol end to
end from a real process. This is NOT the eventual GUI network client
(see the architecture plan's Phase F for that staged migration); it
exists only to drive server_main.py manually for the Part 15/Master Plan
v2 Section 14 acceptance walkthroughs. Real I/O throughout - excluded
from coverage, verified by running it, not by unit tests.

Drives the permanent CLI login flow (Master Plan v2 Decision 2, via
cli_login_flow.CliLoginFlow): username, then password, then either
register or login before anything else is possible. Once authenticated,
offers a choice between the unrated quick_local game (first connection
to ask waits, the second pairs with it) and Phase C's rated "play"
matchmaking queue (+-100 Elo, 1-minute timeout, Decision 5 - typing
"play" again after a timeout re-enters the queue, since there is no
auto-retry). Accepts moves as compact algebraic shorthand ("e2e4")
typed at the prompt - parsed locally into the from_row/from_col/to_row/
to_col JSON payload the server actually expects. The wire protocol
itself is JSON throughout; the shorthand is purely this client's own
input convenience (see the architecture plan's JSON-vs-shorthand
decision).

Phase D (Decision 7): if the connection drops mid-game, this process
automatically reconnects using the session token it already holds in
memory (no re-login) - the server is the sole authority on whether
reconnection is still possible (within the 20-second grace window), so
this client just keeps retrying until either it succeeds or the server
reports there is nothing left to reconnect to.

Phase E (Decision 11): mirrors the server's own NDJSON structured
logging convention (kungfu_chess.server.logging_config) into a local
client-side log file - the same JSON-line shape, the same message_id
correlation field, and the same hash_token one-way hashing (never the
plaintext session token) - since this client is the example every
future client implementation follows.
"""
import asyncio
import json
import logging
import sys

import websockets  # pragma: no cover

from kungfu_chess.server import schemas  # pragma: no cover
from kungfu_chess.server.logging_config import NdjsonFormatter, hash_token  # pragma: no cover
from kungfu_chess.server.login_client import perform_login  # pragma: no cover

SERVER_URL = "ws://localhost:8765"  # pragma: no cover
LOG_PATH = "kungfu_chess_client.log"  # pragma: no cover

logger = logging.getLogger("kungfu_chess.client")  # pragma: no cover


def configure_client_logging(log_path=LOG_PATH):  # pragma: no cover
    handler = logging.FileHandler(log_path)
    handler.setFormatter(NdjsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def square_to_cell(square):  # pragma: no cover
    col = ord(square[0]) - ord("a")
    row = 8 - int(square[1])
    return row, col


def parse_move(text):  # pragma: no cover
    text = text.strip().lower()
    if len(text) == 4 and text[0].isalpha() and text[2].isalpha():
        from_row, from_col = square_to_cell(text[0:2])
        to_row, to_col = square_to_cell(text[2:4])
        return from_row, from_col, to_row, to_col
    return None


def render_board(board_rows):  # pragma: no cover
    for row in board_rows:
        print(" ".join(f"{cell:>3}" for cell in row))


async def receive_loop(websocket, state):  # pragma: no cover
    async for raw in websocket:
        envelope = json.loads(raw)
        msg_type, payload = envelope["type"], envelope["payload"]

        if envelope.get("game_id"):
            state["game_id"] = envelope["game_id"]

        logger.info(
            "received %s", msg_type,
            extra={"message_id": envelope.get("message_id"), "game_id": envelope.get("game_id")})

        if msg_type == "state_snapshot":
            print(f"\n[state_snapshot] sequence={payload['sequence']}")
            render_board(payload["board"])
        elif msg_type == "game_started":
            print(f"\n[game_started] white={payload['white']} black={payload['black']}")
            render_board(payload["state_snapshot"]["board"])
        elif msg_type == "game_event":
            captured = f" captured {payload['captured']}" if payload["captured"] else ""
            print(f"\n[game_event] {payload['kind']}: {payload['from']} -> {payload['to']}{captured}")
        elif msg_type == "game_over":
            print(f"\n[game_over] winner={payload['winner']}")
            state["game_over"] = True
        elif msg_type == "searching_match":
            print("\n[searching_match] waiting for a ranked opponent...")
        elif msg_type == "matchmaking_timeout":
            print("\n[matchmaking_timeout] no opponent found - type 'play' to search again.")
        elif msg_type == "move_rejected":
            print(f"\n[move_rejected] {payload['reason']}")
        elif msg_type == "error":
            print(f"\n[error] {payload['code']}: {payload.get('message', '')}")
        elif msg_type in ("move_accepted", "pong"):
            pass
        else:
            print(f"\n[{msg_type}] {payload}")
        print("move> ", end="", flush=True)


async def send_loop(websocket, state):  # pragma: no cover
    loop = asyncio.get_event_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, input, "move> ")
        except EOFError:
            return  # stdin closed (e.g. piped input exhausted) - exit quietly
        if line.strip().lower() == "play":
            # Decision 5: no auto-retry after a matchmaking timeout - the
            # player must explicitly search again.
            await websocket.send(schemas.encode(schemas.make_envelope("play", {})))
            continue
        move = parse_move(line)
        if move is None:
            print("Type a move like 'e2e4' (from-square to-square), or Ctrl+C to quit.")
            continue
        from_row, from_col, to_row, to_col = move
        envelope = schemas.make_envelope(
            "move_request",
            {"from_row": from_row, "from_col": from_col, "to_row": to_row, "to_col": to_col},
            game_id=state.get("game_id"))
        logger.info(
            "sending move_request", extra={
                "message_id": envelope["message_id"], "game_id": envelope["game_id"]})
        await websocket.send(schemas.encode(envelope))


async def _attempt_reconnect(websocket, session_token):  # pragma: no cover
    logger.info("attempting reconnect", extra={"session_token_hash": hash_token(session_token)})
    await websocket.send(schemas.encode(schemas.make_envelope(
        "reconnect", {"session_token": session_token})))
    response = json.loads(await websocket.recv())
    if response["type"] == "error":
        print(f"Reconnect failed: {response['payload']['code']}")
        return None
    print("Reconnected.")
    render_board(response["payload"]["board"])
    return response.get("game_id")


async def _play_session(websocket, state):  # pragma: no cover
    """Runs receive_loop/send_loop concurrently until either ends,
    cancelling whichever is still running - unlike a plain
    asyncio.gather, this never leaves an orphaned task (e.g. send_loop
    still blocked on input()) running against a connection main() is
    about to replace with a reconnect attempt. Re-raises whichever
    exception ended the session, so main() can distinguish "the
    connection dropped" (reconnect) from "the user quit" (exit)."""
    tasks = [
        asyncio.create_task(receive_loop(websocket, state)),
        asyncio.create_task(send_loop(websocket, state)),
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    for task in done:
        exc = task.exception()
        if exc is not None:
            raise exc


async def main():  # pragma: no cover
    session_token = None

    while True:
        state = {"game_id": None, "game_over": False}
        try:
            async with websockets.connect(SERVER_URL) as websocket:
                if session_token is not None:
                    game_id = await _attempt_reconnect(websocket, session_token)
                    if game_id is None:
                        return
                    state["game_id"] = game_id
                else:
                    flow = await perform_login(websocket)
                    if flow is None:
                        return
                    session_token = flow.session_token
                    logger.info(
                        "logged in as %s", flow.username,
                        extra={"session_token_hash": hash_token(session_token)})

                    mode = input("[Q]uick local or ranked [p]lay? [Q/p]: ").strip().lower()
                    if mode.startswith("p"):
                        await websocket.send(schemas.encode(schemas.make_envelope("play", {})))
                        print(f"Logged in as {flow.username}. Searching for a ranked match...")
                    else:
                        await websocket.send(schemas.encode(schemas.make_envelope(
                            "join_game", {"mode": "quick_local"})))
                        print(f"Logged in as {flow.username}. Waiting for an opponent...")

                await _play_session(websocket, state)
                return  # send_loop/receive_loop ended cleanly (EOF, game over) - done
        except websockets.exceptions.ConnectionClosed:
            if state["game_over"] or session_token is None:
                return
            print("\nConnection lost - attempting to reconnect...")
            continue
        except KeyboardInterrupt:
            return


if __name__ == "__main__":  # pragma: no cover
    configure_client_logging()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
