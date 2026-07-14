from kungfu_chess.gui.board_geometry import cell_to_pixel
from kungfu_chess.io.board_view import BoardRenderer


def render(board, renderer, sprite_library, image_w, image_h, state="idle", frame_index=0):
    """Composes a full frame by drawing every occupied cell through the
    injected Renderer. Not dependent on Img/cv2 directly - all real
    drawing happens inside whatever Renderer implementation is passed
    in (see renderer.py / img_renderer.py)."""
    cell_w = image_w // board.cols
    cell_h = image_h // board.rows

    for row_index, row in enumerate(BoardRenderer.to_rows(board)):
        for col_index, token in enumerate(row):
            if token == ".":
                continue

            frames, _config = sprite_library.load(token, state)
            x, y = cell_to_pixel(row_index, col_index, cell_w, cell_h)
            renderer.draw_sprite(frames[frame_index], x, y, (cell_w, cell_h))
