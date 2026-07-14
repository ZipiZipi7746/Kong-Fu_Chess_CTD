from kungfu_chess.model.board import Board
from kungfu_chess.gui.board_renderer_gui import render


def make_board(rows):
    return Board(rows)


class FakeRenderer:
    """Injected via DI - records draw_sprite calls with no real Img/cv2
    involved at all."""

    def __init__(self):
        self.calls = []

    def draw_sprite(self, path, x, y, size):
        self.calls.append((path, x, y, size))


class FakeSpriteLibrary:
    """Injected via DI - returns deterministic fake frame paths without
    touching disk."""

    def __init__(self):
        self.requested = []

    def load(self, piece_code, state):
        self.requested.append((piece_code, state))
        frames = [f"{piece_code}/{state}/{i}.png" for i in range(1, 6)]
        return frames, {"graphics": {"is_loop": True}}


class TestRender:
    def test_draws_each_occupied_cell_at_its_pixel_position(self):
        board = make_board([["wR", ".", "bK"]])
        renderer = FakeRenderer()
        sprite_library = FakeSpriteLibrary()

        render(board, renderer, sprite_library, image_w=300, image_h=100)

        assert renderer.calls == [
            ("wR/idle/1.png", 0, 0, (100, 100)),
            ("bK/idle/1.png", 200, 0, (100, 100)),
        ]

    def test_skips_empty_cells(self):
        board = make_board([[".", "."]])
        renderer = FakeRenderer()
        sprite_library = FakeSpriteLibrary()

        render(board, renderer, sprite_library, image_w=200, image_h=100)

        assert renderer.calls == []

    def test_uses_idle_state_and_first_frame_by_default(self):
        board = make_board([["wP"]])
        renderer = FakeRenderer()
        sprite_library = FakeSpriteLibrary()

        render(board, renderer, sprite_library, image_w=100, image_h=100)

        assert sprite_library.requested == [("wP", "idle")]
        assert renderer.calls[0][0] == "wP/idle/1.png"

    def test_cell_size_derives_from_image_size_and_board_shape(self):
        # 8x8 board, 822x828 image (matching real board.png), not a
        # hardcoded constant anywhere.
        board = make_board([["wK"] + ["."] * 7 for _ in range(8)])
        renderer = FakeRenderer()
        sprite_library = FakeSpriteLibrary()

        render(board, renderer, sprite_library, image_w=822, image_h=828)

        expected_cell = (822 // 8, 828 // 8)
        assert renderer.calls[0][3] == expected_cell
