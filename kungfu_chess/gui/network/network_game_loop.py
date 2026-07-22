"""Real I/O only (window, mouse, timing, sockets) - pragma: no cover
throughout, same treatment as gui/game_loop.py and server/server_main.py.

Phase F Milestone 1: the networked analogue of gui/game_loop.py. Reuses
ImgRenderer/ViewModelRegistry/SpriteLibrary/HUD exactly as the local
game does - only the data source changes (a websocket connection
instead of a locally-constructed GameEngine.advance_time loop). Also
reuses game_loop.py's own _draw_side_panels/_draw_game_over_overlay/
_use_hand_cursor and window constants directly rather than duplicating
them - this file's own _draw_cell_highlights is a separate, smaller
variant that drops the legal-destination glow (no RuleEngine is
available client-side by design: the server remains the sole rules
authority, Master Plan v2 Section 1).

Never imports kungfu_chess.rules/realtime for decision-making - Board/
Piece are used here purely as inert, already-tested rendering data
containers (exactly how BoardRenderer/ViewModelRegistry already treat
them), never to compute legality or timing locally.

Covers every join path the text reference_client.py already does:
quick_local, ranked play, and Phase E rooms (as the creator/White,
the second joiner/Black, or a read-only spectator - my_color is None
for a spectator, which NetworkGameController already handles correctly
with no special-casing: no token ever equals None). Also mirrors
reference_client.py's Phase D auto-reconnect (network_gui_main.py drives
the retry loop; run()'s optional `resume` parameter lets it skip
straight back into the render loop with the already-known game_id/
board_rows/my_color instead of re-running the join handshake).

Phase E (Decision 11): logs every received message and every outgoing
move/jump request on the same "kungfu_chess.client" logger
network_gui_main.py configures at startup - mirrors reference_client.py's
receive_loop/send_loop logging exactly (message_id/game_id correlation
fields, never a plaintext session token).
"""
import asyncio
import json
import logging
import time

import cv2  # pragma: no cover
import numpy as np  # pragma: no cover

from kungfu_chess.engine.events import MoveResolvedEvent  # pragma: no cover
from kungfu_chess.model.board import Board  # pragma: no cover
from kungfu_chess.model.piece import Piece  # pragma: no cover
from kungfu_chess.gui.game_loop import (  # pragma: no cover
    WINDOW_NAME,
    PANEL_WIDTH,
    SELECTED_COLOR,
    COOLDOWN_COLOR,
    _draw_side_panels,
    _draw_game_over_overlay,
    _use_hand_cursor,
)
from kungfu_chess.gui.geometry.board_geometry import (  # pragma: no cover
    cell_to_pixel,
    compute_letterbox,
    derive_cell_size,
    letterbox_screen_to_image,
)
from kungfu_chess.gui.gui_config import DEFAULT_BOARD_IMAGE_PATH, DEFAULT_PIECES_ROOT  # pragma: no cover
from kungfu_chess.gui.rendering.img_adapter import Img  # pragma: no cover
from kungfu_chess.gui.rendering.img_renderer import ImgRenderer  # pragma: no cover
from kungfu_chess.gui.hud.observers import MovesLogObserver, ScoreObserver  # pragma: no cover
from kungfu_chess.gui.animation.sprite_library import SpriteLibrary  # pragma: no cover
from kungfu_chess.gui.animation.view_model_registry import ViewModelRegistry  # pragma: no cover
from kungfu_chess.input.board_mapper import BoardMapper  # pragma: no cover
from kungfu_chess.gui.network.network_engine_view import NetworkEngineView  # pragma: no cover
from kungfu_chess.gui.network.network_game_controller import NetworkGameController  # pragma: no cover
from kungfu_chess.server import protocol, schemas  # pragma: no cover

logger = logging.getLogger("kungfu_chess.client")  # pragma: no cover


def _draw_cell_highlights(board_renderer, board, controller, cell_w, cell_h):  # pragma: no cover
    """The cooldown sandclock fill (identical to game_loop.py's) plus a
    selected-cell highlight - no legal-destination glow, since no
    RuleEngine exists on this side of the network."""
    for row in range(board.rows):
        for col in range(board.cols):
            progress = controller.engine.cooldown_progress(row, col)
            if progress is None:
                continue
            cx, cy = cell_to_pixel(row, col, cell_w, cell_h)
            fill_h = int(cell_h * (1 - progress))
            if fill_h <= 0:
                continue
            board_renderer.draw_highlight(cx, cy + (cell_h - fill_h), (cell_w, fill_h), COOLDOWN_COLOR)

    if controller.selected is not None:
        sel_row, sel_col = controller.selected
        if board.get_cell(sel_row, sel_col) is not None:
            sx, sy = cell_to_pixel(sel_row, sel_col, cell_w, cell_h)
            board_renderer.draw_highlight(sx, sy, (cell_w, cell_h), SELECTED_COLOR)


async def await_fresh_game_start(websocket, my_username):  # pragma: no cover
    """Blocks until game_started arrives, tracking the game_id and
    initial board along the way - used for quick_local, ranked play, a
    room's creator (White) waiting for a second joiner, and a room's
    second joiner (Black) once join_game_as_room has confirmed that
    role. Returns (game_id, board_rows, my_color), or (None, None, None)
    if the connection closes or matchmaking times out (Decision 5: no
    auto-retry - the caller reports this and exits)."""
    game_id, board_rows = None, None
    async for raw in websocket:
        envelope = json.loads(raw)
        msg_type, payload = envelope["type"], envelope["payload"]
        if envelope.get("game_id"):
            game_id = envelope["game_id"]

        if msg_type == protocol.STATE_SNAPSHOT:
            board_rows = payload["board"]
        elif msg_type == protocol.GAME_STARTED:
            board_rows = payload["state_snapshot"]["board"]
            my_color = "w" if payload["white"] == my_username else "b"
            return game_id, board_rows, my_color
        elif msg_type == protocol.MATCHMAKING_TIMEOUT:
            print("No ranked opponent found within the search window.")
            return None, None, None
    return None, None, None


async def join_game_as_room(websocket, room_id, my_username):  # pragma: no cover
    """Sends join_room and returns (game_id, board_rows, my_color) once
    the join is fully resolved - my_color is "b" for the second joiner
    (who also starts the game, same as await_fresh_game_start) or None
    for a spectator (a read-only observer; NetworkGameController already
    handles my_color=None correctly with no special-casing). Returns
    (None, None, None) on a rejected join_room (unknown room, spectator
    cap reached)."""
    await websocket.send(schemas.encode(schemas.make_envelope(
        protocol.JOIN_ROOM, {"room_id": room_id})))
    ack = json.loads(await websocket.recv())
    if ack["type"] == protocol.ERROR:
        print(f"Could not join room: {ack['payload']['code']}")
        return None, None, None

    role = ack["payload"]["role"]
    if role == "black":
        return await await_fresh_game_start(websocket, my_username)

    # role == "spectator": the game is already running - the very next
    # message is the catch-up state_snapshot itself (never a
    # game_started, which was already broadcast to the two players
    # earlier), and there is no color to assign.
    snapshot = json.loads(await websocket.recv())
    return snapshot["game_id"], snapshot["payload"]["board"], None


async def _receive_loop(websocket, state, engine_view, moves_log, score):  # pragma: no cover
    async for raw in websocket:
        envelope = json.loads(raw)
        msg_type, payload = envelope["type"], envelope["payload"]
        if envelope.get("game_id"):
            state["game_id"] = envelope["game_id"]

        logger.info(
            "received %s", msg_type,
            extra={"message_id": envelope.get("message_id"), "game_id": envelope.get("game_id")})

        if msg_type in (protocol.STATE_SNAPSHOT, protocol.RENDER_STATE):
            state["board_rows"] = payload["board"]
            engine_view.update(payload)
        elif msg_type == protocol.GAME_EVENT:
            moving_piece = Piece.parse(payload["moving_piece"])
            captured_piece = Piece.parse(payload["captured"]) if payload["captured"] else None
            event = MoveResolvedEvent(
                payload["from"][0], payload["from"][1], payload["to"][0], payload["to"][1],
                moving_piece, captured_piece, timestamp_ms=payload.get("timestamp_ms", 0))
            moves_log(event)
            score(event)
        elif msg_type in (protocol.MOVE_REJECTED, protocol.ERROR):
            print(f"[{msg_type}] {payload}")
        elif msg_type == protocol.PLAYER_DISCONNECTED:
            print(f"[player_disconnected] opponent has {payload['grace_period_ms'] // 1000}s to reconnect.")


async def _render_loop(state, controller, moves_log, score,  # pragma: no cover
                        board_image_path, pieces_root):
    base = Img().read(board_image_path)
    image_h, image_w = base.img.shape[:2]
    board_x = PANEL_WIDTH
    content_w = PANEL_WIDTH + image_w + PANEL_WIDTH

    rows = len(state["board_rows"])
    cols = len(state["board_rows"][0])
    cell_size = derive_cell_size(image_w, image_h, rows, cols)
    mapper = BoardMapper(cell_size)

    sprite_library = SpriteLibrary(pieces_root)
    registry = ViewModelRegistry(sprite_library)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, content_w, image_h)
    window_size = {"w": content_w, "h": image_h}

    def on_mouse(event, x, y, flags, param):
        _use_hand_cursor()
        if event not in (cv2.EVENT_LBUTTONDOWN, cv2.EVENT_RBUTTONDOWN):
            return
        mapped = letterbox_screen_to_image(
            x, y, window_size["w"], window_size["h"], content_w, image_h)
        if mapped is None:
            return
        ix, iy = mapped
        if ix < board_x or ix >= board_x + image_w:
            return
        board_ix = ix - board_x
        row, col = mapper.to_cell(board_ix, iy)
        if not (0 <= row < rows and 0 <= col < cols):
            return
        if event == cv2.EVENT_LBUTTONDOWN:
            controller.click(row, col, state["board_rows"])
        else:
            controller.jump(row, col, state["board_rows"])

    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    last_time = time.perf_counter()
    while True:
        now = time.perf_counter()
        dt_ms = int((now - last_time) * 1000)
        last_time = now

        content = Img()
        content.img = np.zeros((image_h, content_w, base.img.shape[2]), dtype=base.img.dtype)
        renderer = ImgRenderer(content)

        board_canvas = Img()
        board_canvas.img = base.img.copy()
        board_renderer = ImgRenderer(board_canvas)

        board = Board(state["board_rows"])
        cell_w = image_w // cols
        cell_h = image_h // rows

        _draw_cell_highlights(board_renderer, board, controller, cell_w, cell_h)
        registry.render(board, board_renderer, controller.engine, image_w, image_h, dt_ms)
        board_canvas.draw_on(content, board_x, 0)

        _draw_side_panels(renderer, board_x, image_w, moves_log, score)
        _draw_game_over_overlay(renderer, controller, board_x, image_w, image_h)

        rect = cv2.getWindowImageRect(WINDOW_NAME)
        window_size["w"], window_size["h"] = max(rect[2], 1), max(rect[3], 1)

        scale, offset_x, offset_y, displayed_w, displayed_h = compute_letterbox(
            window_size["w"], window_size["h"], content_w, image_h)

        padded = np.zeros((window_size["h"], window_size["w"], content.img.shape[2]), dtype=content.img.dtype)
        resized = cv2.resize(content.img, (int(displayed_w), int(displayed_h)))
        x0, y0 = int(offset_x), int(offset_y)
        padded[y0:y0 + resized.shape[0], x0:x0 + resized.shape[1]] = resized

        cv2.imshow(WINDOW_NAME, padded)
        key = cv2.waitKey(16) & 0xFF
        # Yields control back to the event loop each frame so the
        # concurrent _receive_loop task actually gets to process buffered
        # incoming websocket frames between draws.
        await asyncio.sleep(0)
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()


async def run(websocket, my_username, board_image_path=DEFAULT_BOARD_IMAGE_PATH,  # pragma: no cover
               pieces_root=DEFAULT_PIECES_ROOT, resume=None):
    """resume, if given, is (game_id, board_rows, my_color) already
    known from a prior session on this same logical connection (Phase D
    reconnect, driven by network_gui_main.py) - skips the join
    handshake entirely and re-enters the render loop directly."""
    if resume is not None:
        game_id, board_rows, my_color = resume
    else:
        game_id, board_rows, my_color = await await_fresh_game_start(websocket, my_username)
        if board_rows is None:
            print("Connection closed before the game started.")
            return

    state = {"board_rows": board_rows, "game_id": game_id}
    engine_view = NetworkEngineView()

    def send_move_request(from_row, from_col, to_row, to_col):
        envelope = schemas.make_envelope(
            protocol.MOVE_REQUEST,
            {"from_row": from_row, "from_col": from_col, "to_row": to_row, "to_col": to_col},
            game_id=state["game_id"])
        logger.info(
            "sending move_request",
            extra={"message_id": envelope["message_id"], "game_id": envelope["game_id"]})
        asyncio.create_task(websocket.send(schemas.encode(envelope)))

    def send_jump_request(row, col):
        envelope = schemas.make_envelope(
            protocol.JUMP_REQUEST, {"row": row, "col": col}, game_id=state["game_id"])
        logger.info(
            "sending jump_request",
            extra={"message_id": envelope["message_id"], "game_id": envelope["game_id"]})
        asyncio.create_task(websocket.send(schemas.encode(envelope)))

    controller = NetworkGameController(my_color, send_move_request, send_jump_request, engine=engine_view)
    moves_log = MovesLogObserver(len(board_rows))
    score = ScoreObserver()

    tasks = [
        asyncio.create_task(_receive_loop(websocket, state, engine_view, moves_log, score)),
        asyncio.create_task(_render_loop(state, controller, moves_log, score, board_image_path, pieces_root)),
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    for task in done:
        exc = task.exception()
        if exc is not None:
            raise exc
