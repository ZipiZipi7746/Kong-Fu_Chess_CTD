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
"""
import time

import cv2  # pragma: no cover
import numpy as np  # pragma: no cover

from kungfu_chess.gui.board_geometry import (  # pragma: no cover
    compute_letterbox,
    derive_cell_size,
    letterbox_screen_to_image,
)
from kungfu_chess.gui.img_adapter import Img  # pragma: no cover
from kungfu_chess.gui.img_renderer import ImgRenderer  # pragma: no cover
from kungfu_chess.gui.sprite_library import SpriteLibrary  # pragma: no cover
from kungfu_chess.gui.view_model_registry import ViewModelRegistry  # pragma: no cover
from kungfu_chess.input.board_mapper import BoardMapper  # pragma: no cover
from kungfu_chess.input.controller import GameController  # pragma: no cover

WINDOW_NAME = "Kung Fu Chess"  # pragma: no cover


def run(board, board_image_path="assets/board.png",  # pragma: no cover
        pieces_root="assets/pieces_mine"):
    base = Img().read(board_image_path)
    image_h, image_w = base.img.shape[:2]

    cell_size = derive_cell_size(image_w, image_h, board.rows, board.cols)
    controller = GameController(board, mapper=BoardMapper(cell_size))
    sprite_library = SpriteLibrary(pieces_root)
    registry = ViewModelRegistry(sprite_library)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, image_w, image_h)

    window_size = {"w": image_w, "h": image_h}

    def on_mouse(event, x, y, flags, param):
        if event not in (cv2.EVENT_LBUTTONDOWN, cv2.EVENT_RBUTTONDOWN):
            return
        mapped = letterbox_screen_to_image(
            x, y, window_size["w"], window_size["h"], image_w, image_h)
        if mapped is None:
            return  # click landed on a letterbox padding bar, not the board
        ix, iy = mapped
        if event == cv2.EVENT_LBUTTONDOWN:
            controller.click(ix, iy)
        else:
            controller.jump(ix, iy)

    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    last_time = time.perf_counter()
    while True:
        now = time.perf_counter()
        dt_ms = int((now - last_time) * 1000)
        last_time = now
        if dt_ms > 0:
            controller.wait(dt_ms)

        canvas = Img()
        canvas.img = base.img.copy()
        registry.render(board, ImgRenderer(canvas), controller.engine, image_w, image_h, dt_ms)

        rect = cv2.getWindowImageRect(WINDOW_NAME)
        window_size["w"], window_size["h"] = max(rect[2], 1), max(rect[3], 1)

        scale, offset_x, offset_y, displayed_w, displayed_h = compute_letterbox(
            window_size["w"], window_size["h"], image_w, image_h)

        padded = np.zeros((window_size["h"], window_size["w"], canvas.img.shape[2]), dtype=canvas.img.dtype)
        resized = cv2.resize(canvas.img, (int(displayed_w), int(displayed_h)))
        x0, y0 = int(offset_x), int(offset_y)
        padded[y0:y0 + resized.shape[0], x0:x0 + resized.shape[1]] = resized

        cv2.imshow(WINDOW_NAME, padded)
        key = cv2.waitKey(16) & 0xFF
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()
