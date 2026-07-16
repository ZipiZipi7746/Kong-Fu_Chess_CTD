def cell_to_pixel(row, col, cell_w, cell_h):
    """The inverse of BoardMapper.to_cell: the top-left pixel of a board
    cell. cell_w/cell_h are always derived by the caller from the actual
    loaded image size and board shape - never hardcoded here."""
    return col * cell_w, row * cell_h


def derive_cell_size(image_w, image_h, rows, cols):
    """BoardMapper only accepts a single cell_size, not independent
    width/height, so for a non-square image this picks the smaller of
    the two axis-derived sizes - guaranteeing every click inside the
    visible board still maps to a valid, in-bounds cell."""
    return min(image_w // cols, image_h // rows)


def compute_letterbox(window_w, window_h, image_w, image_h):
    """The scale and centering offset to fit image_w x image_h inside
    window_w x window_h while preserving its aspect ratio (letterboxed/
    pillarboxed, never stretched). Returns
    (scale, offset_x, offset_y, displayed_w, displayed_h)."""
    scale = min(window_w / image_w, window_h / image_h)
    displayed_w = image_w * scale
    displayed_h = image_h * scale
    offset_x = (window_w - displayed_w) / 2
    offset_y = (window_h - displayed_h) / 2
    return scale, offset_x, offset_y, displayed_w, displayed_h


def letterbox_screen_to_image(x_screen, y_screen, window_w, window_h, image_w, image_h):
    """Inverts compute_letterbox: maps a window-space coordinate back to
    the original image's pixel space, or None if the point falls in the
    letterbox padding rather than on the displayed image itself."""
    scale, offset_x, offset_y, _, _ = compute_letterbox(window_w, window_h, image_w, image_h)
    x_image = (x_screen - offset_x) / scale
    y_image = (y_screen - offset_y) / scale
    if 0 <= x_image < image_w and 0 <= y_image < image_h:
        return int(x_image), int(y_image)
    return None
