"""Real I/O: the graphical login/menu/waiting screen loop - pragma: no
cover throughout, same treatment as gui/game_loop.py and
gui/network/network_game_loop.py. Runs the same cv2 window (WINDOW_NAME,
reused from gui/game_loop.py) through the pre-game screens (login ->
menu -> waiting) before handing off to network_game_loop.run() for the
actual board.

Keyboard input uses cv2.waitKey()'s raw ASCII-range key codes (printable
chars, Backspace=8, Tab=9, Esc=27) - basic but sufficient for username/
password/room-code entry; no cursor positioning, text selection, or IME
support.
"""
import asyncio

import cv2  # pragma: no cover
import numpy as np  # pragma: no cover

from kungfu_chess.gui.game_loop import WINDOW_NAME  # pragma: no cover
from kungfu_chess.gui.network import screen_rendering  # pragma: no cover
from kungfu_chess.gui.rendering.img_adapter import Img  # pragma: no cover
from kungfu_chess.gui.rendering.img_renderer import ImgRenderer  # pragma: no cover

CONTENT_W = 800  # pragma: no cover
CONTENT_H = 600  # pragma: no cover
BACKGROUND_COLOR = (30, 30, 30, 255)  # pragma: no cover


def _draw_instructions(renderer, instructions):  # pragma: no cover
    for instruction in instructions:
        kind = instruction[0]
        if kind == "rect":
            _, x, y, w, h, color = instruction
            renderer.draw_highlight(x, y, (w, h), color)
        else:
            _, text, x, y, color = instruction
            renderer.draw_text(text, x, y, color=color)


def _new_canvas():  # pragma: no cover
    canvas = Img()
    canvas.img = np.full((CONTENT_H, CONTENT_W, 4), BACKGROUND_COLOR, dtype=np.uint8)
    return canvas


def _handle_key(screen, key):  # pragma: no cover
    if key == 8 and hasattr(screen, "handle_backspace"):
        screen.handle_backspace()
    elif key == 9 and hasattr(screen, "handle_tab"):
        screen.handle_tab()
    elif 32 <= key < 127 and hasattr(screen, "handle_char"):
        screen.handle_char(chr(key))


async def run_screen(screen, render_fn, *render_args):  # pragma: no cover
    """Draws `screen` via render_fn(screen, *render_args) every frame,
    routes left-clicks to screen.handle_click and keyboard to
    handle_char/handle_backspace/handle_tab (whichever the screen
    defines), and returns the first non-None action handle_click
    produces - or None if the window was closed (ESC)."""
    result = {"action": None}

    def on_mouse(event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        action = screen.handle_click(x, y)
        if action is not None:
            result["action"] = action

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, CONTENT_W, CONTENT_H)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    while result["action"] is None:
        canvas = _new_canvas()
        renderer = ImgRenderer(canvas)
        _draw_instructions(renderer, render_fn(screen, *render_args))
        cv2.imshow(WINDOW_NAME, canvas.img)

        key = cv2.waitKey(16) & 0xFF
        await asyncio.sleep(0)
        if key == 27:  # ESC
            return None
        _handle_key(screen, key)

    return result["action"]


async def run_waiting_screen(screen, network_task):  # pragma: no cover
    """Draws a WaitingScreen every frame until either the user clicks
    Cancel or `network_task` (an already-created asyncio.Task awaiting
    the actual server response) completes - whichever happens first.
    Returns ("completed", network_task's result) or ("cancelled", None).
    """
    cancelled = {"value": False}

    def on_mouse(event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if screen.handle_click(x, y) == "cancel":
            cancelled["value"] = True

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, CONTENT_W, CONTENT_H)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    while not network_task.done() and not cancelled["value"]:
        canvas = _new_canvas()
        renderer = ImgRenderer(canvas)
        _draw_instructions(renderer, screen_rendering.render_waiting_screen(screen))
        cv2.imshow(WINDOW_NAME, canvas.img)

        key = cv2.waitKey(16) & 0xFF
        await asyncio.sleep(0)
        if key == 27:
            cancelled["value"] = True

    if cancelled["value"]:
        network_task.cancel()
        return "cancelled", None
    return "completed", network_task.result()
