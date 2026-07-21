"""Throwaway reference client - validates the WebSocket protocol end to
end from a real process. This is NOT the eventual GUI network client
(see the architecture plan's Phase F for that staged migration); it
exists only to drive server_main.py manually for the Part 15/Master Plan
v2 Section 14 acceptance walkthroughs. Real I/O throughout - excluded
from coverage, verified by running it, not by unit tests.

Drives the permanent CLI login flow (Master Plan v2 Decision 2, via
cli_login_flow.CliLoginFlow): username, then password, then either
register or login before anything else is possible. Once authenticated,
joins the shared quick_local game and accepts moves as compact
algebraic shorthand ("e2e4") typed at the prompt - parsed locally into
the from_row/from_col/to_row/to_col JSON payload the server actually
expects. The wire protocol itself is JSON throughout; the shorthand is
purely this client's own input convenience (see the architecture plan's
JSON-vs-shorthand decision).
"""
import asyncio
import json
import sys

import websockets  # pragma: no cover

from kungfu_chess.server import schemas  # pragma: no cover
from kungfu_chess.server.login_client import perform_login  # pragma: no cover

SERVER_URL = "ws://localhost:8765"  # pragma: no cover


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
        move = parse_move(line)
        if move is None:
            print("Type a move like 'e2e4' (from-square to-square), or Ctrl+C to quit.")
            continue
        from_row, from_col, to_row, to_col = move
        await websocket.send(schemas.encode(schemas.make_envelope(
            "move_request",
            {"from_row": from_row, "from_col": from_col, "to_row": to_row, "to_col": to_col},
            game_id=state.get("game_id"))))


async def main():  # pragma: no cover
    state = {"game_id": None, "game_over": False}

    async with websockets.connect(SERVER_URL) as websocket:
        flow = await perform_login(websocket)
        if flow is None:
            return

        await websocket.send(schemas.encode(schemas.make_envelope(
            "join_game", {"mode": "quick_local"})))
        print(f"Logged in as {flow.username}. Waiting for an opponent...")

        try:
            await asyncio.gather(
                receive_loop(websocket, state),
                send_loop(websocket, state),
            )
        except (websockets.exceptions.ConnectionClosed, KeyboardInterrupt):
            pass


if __name__ == "__main__":  # pragma: no cover
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
