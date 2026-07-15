"""Real I/O only (window, mouse, timing) - # pragma: no cover throughout,
same treatment as BoardParser._read_stdin and phase0_pixel_check.py.

Connects the animated (Phase 3) rendering to a live window and the
existing GameController.click/jump/wait - without changing a single
line in GameController itself. Left-click = click(), right-click =
jump(), ESC = quit.

The board is displayed letterboxed (aspect-ratio preserved, padded with
black bars) rather than stretched to fill the window (Phase 4) - cv2's
own stretch-to-fill would otherwise distort the board on a non-uniform
resize. Click coordinates are mapped back through the same letterbox
transform (compute_letterbox / letterbox_screen_to_image), which is
genuinely needed here - unlike Phase 0's screen_to_image, which turned
out to double-correct because cv2 already maps clicks into image space
on this backend when it does its own (undistorted) scaling.

Phase 5 adds two side panels (score / moves log / player name), one per
color, flanking the board - Black's on the left, White's on the right.
The "content" being letterboxed is the whole
left-panel+board+right-panel canvas; clicks landing in either panel
(x before or past the board's own span) are simply ignored rather than
passed to the controller.
"""
import time

import cv2  # pragma: no cover
import numpy as np  # pragma: no cover

from kungfu_chess.engine.events import EventBus  # pragma: no cover
from kungfu_chess.engine.game_engine import GameEngine  # pragma: no cover
from kungfu_chess.gui.board_geometry import (  # pragma: no cover
    cell_to_pixel,
    compute_letterbox,
    derive_cell_size,
    letterbox_screen_to_image,
)
from kungfu_chess.gui.hud import (  # pragma: no cover
    render_game_over,
    render_moves_log,
    render_player_name,
    render_score,
)
from kungfu_chess.gui.img_adapter import Img  # pragma: no cover
from kungfu_chess.gui.img_renderer import ImgRenderer  # pragma: no cover
from kungfu_chess.gui.legal_moves import legal_destinations  # pragma: no cover
from kungfu_chess.gui.observers import MovesLogObserver, ScoreObserver  # pragma: no cover
from kungfu_chess.gui.sprite_library import SpriteLibrary  # pragma: no cover
from kungfu_chess.gui.view_model_registry import ViewModelRegistry  # pragma: no cover
from kungfu_chess.input.board_mapper import BoardMapper  # pragma: no cover
from kungfu_chess.input.controller import GameController  # pragma: no cover

WINDOW_NAME = "Kung Fu Chess"  # pragma: no cover
PANEL_WIDTH = 220  # pragma: no cover
SELECTED_COLOR = (0, 215, 255, 130)  # pragma: no cover
LEGAL_MOVE_COLOR = (0, 200, 0, 100)  # pragma: no cover
GAME_OVER_OVERLAY_COLOR = (0, 0, 0, 170)  # pragma: no cover
GAME_OVER_TEXT_COLOR = (0, 215, 255, 255)  # pragma: no cover
GAME_OVER_OVERLAY_HEIGHT = 80  # pragma: no cover


def run(board, board_image_path="assets/board.png",  # pragma: no cover
        pieces_root="assets/pieces_mine"):
    base = Img().read(board_image_path)
    image_h, image_w = base.img.shape[:2]
    board_x = PANEL_WIDTH  # black panel occupies [0, PANEL_WIDTH); board starts here
    content_w = PANEL_WIDTH + image_w + PANEL_WIDTH

    cell_size = derive_cell_size(image_w, image_h, board.rows, board.cols)

    event_bus = EventBus()
    moves_log = MovesLogObserver(board.rows)
    score = ScoreObserver()
    event_bus.subscribe(moves_log)
    event_bus.subscribe(score)

    engine = GameEngine(board, jump_duration_ms=1000, event_bus=event_bus)
    controller = GameController(board, mapper=BoardMapper(cell_size), engine=engine)
    sprite_library = SpriteLibrary(pieces_root)
    registry = ViewModelRegistry(sprite_library)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, content_w, image_h)

    window_size = {"w": content_w, "h": image_h}

    def on_mouse(event, x, y, flags, param):
        if event not in (cv2.EVENT_LBUTTONDOWN, cv2.EVENT_RBUTTONDOWN):
            return
        mapped = letterbox_screen_to_image(
            x, y, window_size["w"], window_size["h"], content_w, image_h)
        if mapped is None:
            return  # click landed on a letterbox padding bar
        ix, iy = mapped
        if ix < board_x or ix >= board_x + image_w:
            return  # click landed on a side panel, not the board
        board_ix = ix - board_x
        if event == cv2.EVENT_LBUTTONDOWN:
            controller.click(board_ix, iy)
        else:
            controller.jump(board_ix, iy)

    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    last_time = time.perf_counter()
    while True:
        now = time.perf_counter()
        dt_ms = int((now - last_time) * 1000)
        last_time = now
        if dt_ms > 0:
            controller.wait(dt_ms)

        content = Img()
        content.img = np.zeros((image_h, content_w, base.img.shape[2]), dtype=base.img.dtype)
        renderer = ImgRenderer(content)

        board_canvas = Img()
        board_canvas.img = base.img.copy()
        board_renderer = ImgRenderer(board_canvas)

        # Highlights are drawn before the pieces, so they show as
        # colored squares behind them rather than covering them.
        cell_w = image_w // board.cols
        cell_h = image_h // board.rows
        if controller.selected is not None:
            sel_row, sel_col = controller.selected
            selected_piece = board.get_cell(sel_row, sel_col)
            if selected_piece is not None:
                sx, sy = cell_to_pixel(sel_row, sel_col, cell_w, cell_h)
                board_renderer.draw_highlight(sx, sy, (cell_w, cell_h), SELECTED_COLOR)
                for row, col in legal_destinations(
                        selected_piece, sel_row, sel_col, board, controller.engine.rule_engine):
                    dx, dy = cell_to_pixel(row, col, cell_w, cell_h)
                    board_renderer.draw_highlight(dx, dy, (cell_w, cell_h), LEGAL_MOVE_COLOR)

        registry.render(board, board_renderer, controller.engine, image_w, image_h, dt_ms)
        board_canvas.draw_on(content, board_x, 0)

        black_panel_x, white_panel_x = 16, board_x + image_w + 16
        for panel_x, name, moves, player_score in (
                (black_panel_x, "Black", moves_log.black_moves, score.black_score),
                (white_panel_x, "White", moves_log.white_moves, score.white_score)):
            for text, x, y in render_player_name(name, panel_x, 24):
                renderer.draw_text(text, x, y)
            for text, x, y in render_score(player_score, panel_x, 60):
                renderer.draw_text(text, x, y)
            for text, x, y in render_moves_log(moves, panel_x, 100, line_height=18):
                renderer.draw_text(text, x, y, font_size=0.4)

        if controller.engine.game_over and controller.engine.winner is not None:
            overlay_y = image_h // 2 - GAME_OVER_OVERLAY_HEIGHT // 2
            renderer.draw_highlight(
                board_x, overlay_y, (image_w, GAME_OVER_OVERLAY_HEIGHT), GAME_OVER_OVERLAY_COLOR)
            for text, x, y in render_game_over(
                    controller.engine.winner, board_x + image_w // 2 - 110, image_h // 2 + 12):
                renderer.draw_text(text, x, y, font_size=1.2, color=GAME_OVER_TEXT_COLOR, thickness=3)

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
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()
