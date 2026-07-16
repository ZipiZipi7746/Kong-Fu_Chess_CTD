from kungfu_chess.gui.geometry.board_geometry import (
    cell_to_pixel,
    compute_letterbox,
    derive_cell_size,
    letterbox_screen_to_image,
)


class TestCellToPixel:
    def test_top_left_cell_is_at_origin(self):
        assert cell_to_pixel(0, 0, cell_w=100, cell_h=100) == (0, 0)

    def test_scales_by_column_and_row(self):
        assert cell_to_pixel(row=2, col=3, cell_w=100, cell_h=100) == (300, 200)

    def test_non_square_cells(self):
        assert cell_to_pixel(row=1, col=1, cell_w=822 // 8, cell_h=828 // 8) == (822 // 8, 828 // 8)

    def test_different_board_sizes_use_the_same_formula(self):
        # a 10x10 board with its own derived cell size
        assert cell_to_pixel(row=4, col=7, cell_w=64, cell_h=64) == (448, 256)


class TestDeriveCellSize:
    def test_exact_square_division(self):
        assert derive_cell_size(image_w=800, image_h=800, rows=8, cols=8) == 100

    def test_non_square_image_picks_the_smaller_axis(self):
        # 822x828 board.png over an 8x8 board: width gives 102, height
        # gives 103 - picking the smaller keeps every click in-bounds,
        # since BoardMapper only accepts a single cell_size.
        assert derive_cell_size(image_w=822, image_h=828, rows=8, cols=8) == 102

    def test_different_board_shape(self):
        assert derive_cell_size(image_w=640, image_h=640, rows=10, cols=10) == 64


class TestComputeLetterbox:
    def test_window_matches_image_aspect_no_padding(self):
        scale, offset_x, offset_y, displayed_w, displayed_h = compute_letterbox(
            window_w=800, window_h=800, image_w=800, image_h=800)
        assert (scale, offset_x, offset_y, displayed_w, displayed_h) == (1, 0, 0, 800, 800)

    def test_wider_window_pillarboxes(self):
        # window is much wider than the (square) image - bars on left/right
        scale, offset_x, offset_y, displayed_w, displayed_h = compute_letterbox(
            window_w=1600, window_h=800, image_w=800, image_h=800)
        assert scale == 1
        assert (displayed_w, displayed_h) == (800, 800)
        assert (offset_x, offset_y) == (400, 0)

    def test_taller_window_letterboxes(self):
        # window is much taller than the (square) image - bars on top/bottom
        scale, offset_x, offset_y, displayed_w, displayed_h = compute_letterbox(
            window_w=800, window_h=1600, image_w=800, image_h=800)
        assert scale == 1
        assert (displayed_w, displayed_h) == (800, 800)
        assert (offset_x, offset_y) == (0, 400)

    def test_scales_up_uniformly_when_window_is_bigger(self):
        scale, offset_x, offset_y, displayed_w, displayed_h = compute_letterbox(
            window_w=1600, window_h=1600, image_w=800, image_h=800)
        assert scale == 2
        assert (displayed_w, displayed_h) == (1600, 1600)
        assert (offset_x, offset_y) == (0, 0)

    def test_non_square_image_in_a_square_window(self):
        scale, offset_x, offset_y, displayed_w, displayed_h = compute_letterbox(
            window_w=800, window_h=800, image_w=800, image_h=400)
        assert scale == 1
        assert (displayed_w, displayed_h) == (800, 400)
        assert (offset_x, offset_y) == (0, 200)


class TestLetterboxScreenToImage:
    def test_identity_when_window_matches_image(self):
        assert letterbox_screen_to_image(100, 200, window_w=800, window_h=800,
                                          image_w=800, image_h=800) == (100, 200)

    def test_click_inside_the_displayed_image_in_a_pillarboxed_window(self):
        # 1600x800 window, 800x800 image -> displayed 800x800 at offset_x=400
        assert letterbox_screen_to_image(400, 0, window_w=1600, window_h=800,
                                          image_w=800, image_h=800) == (0, 0)
        assert letterbox_screen_to_image(800, 400, window_w=1600, window_h=800,
                                          image_w=800, image_h=800) == (400, 400)

    def test_click_in_the_left_padding_bar_returns_none(self):
        assert letterbox_screen_to_image(100, 400, window_w=1600, window_h=800,
                                          image_w=800, image_h=800) is None

    def test_click_in_the_right_padding_bar_returns_none(self):
        assert letterbox_screen_to_image(1500, 400, window_w=1600, window_h=800,
                                          image_w=800, image_h=800) is None

    def test_click_in_the_top_padding_bar_returns_none(self):
        assert letterbox_screen_to_image(400, 50, window_w=800, window_h=1600,
                                          image_w=800, image_h=800) is None
