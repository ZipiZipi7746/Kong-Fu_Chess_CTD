"""Phase 0 (build plan Section 3): a standalone calibration script, not
part of the final UI. Confirms the screen-to-image pixel mapping is
correct - including under window resize - before anything is wired to
real game logic. Run it directly and check the marker tracks the mouse
exactly; this file has no automated test, same as BoardParser._read_stdin,
since it requires a real window and a human eye.

Empirically, this backend's cv2.setMouseCallback already reports
coordinates in the original image's pixel space, even when the window
has been resized - so no manual screen_to_image() correction is applied
here (doing so double-corrected and made the marker drift further off
the further the window was enlarged). screen_to_image() itself stays in
board_geometry.py as a validated, reusable utility for a context that
does hand us raw, unscaled window coordinates.
"""
import cv2  # pragma: no cover

from kungfu_chess.gui.img_adapter import Img  # pragma: no cover

WINDOW_NAME = "Phase 0 - pixel mapping check"  # pragma: no cover

_state = {"hover": None, "click": None}  # pragma: no cover


def _on_mouse(event, x, y, flags, param):  # pragma: no cover
    _state["hover"] = (x, y)
    if event == cv2.EVENT_LBUTTONDOWN:
        _state["click"] = (x, y)


def run(board_path="assets/board.png"):  # pragma: no cover
    base = Img().read(board_path)
    image_h, image_w = base.img.shape[:2]

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, image_w, image_h)
    cv2.setMouseCallback(WINDOW_NAME, _on_mouse)

    while True:
        frame = Img()
        frame.img = base.img.copy()

        if _state["hover"] is not None:
            cv2.drawMarker(frame.img, _state["hover"], (255, 0, 0, 255),
                            markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)
        if _state["click"] is not None:
            cv2.drawMarker(frame.img, _state["click"], (0, 0, 255, 255),
                            markerType=cv2.MARKER_TILTED_CROSS, markerSize=24, thickness=3)

        cv2.imshow(WINDOW_NAME, frame.img)
        key = cv2.waitKey(16) & 0xFF
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":  # pragma: no cover
    run()
