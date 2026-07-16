from kungfu_chess.model.board import Board
from kungfu_chess.gui.animation.view_model_registry import ViewModelRegistry


CONFIGS = {
    "idle": {"physics": {"next_state_when_finished": "idle"},
              "graphics": {"frames_per_sec": 4, "is_loop": True}},
    "move": {"physics": {"next_state_when_finished": "long_rest"},
              "graphics": {"frames_per_sec": 8, "is_loop": True}},
    "jump": {"physics": {"next_state_when_finished": "short_rest"},
              "graphics": {"frames_per_sec": 10, "is_loop": False}},
    "short_rest": {"physics": {"next_state_when_finished": "long_rest"},
                    "graphics": {"frames_per_sec": 6, "is_loop": False}},
    "long_rest": {"physics": {"next_state_when_finished": "idle"},
                   "graphics": {"frames_per_sec": 2, "is_loop": False}},
}


class FakeSpriteLibrary:
    def load(self, piece_code, state):
        frames = [f"{piece_code}/{state}/{i}.png" for i in range(1, 6)]
        return frames, CONFIGS[state]


class FakeRenderer:
    def __init__(self):
        self.calls = []

    def draw_sprite(self, path, x, y, size):
        self.calls.append((path, x, y, size))


class FakeEngine:
    def __init__(self, pending_from=None, airborne=None, progress=None, targets=None):
        self._pending_from = pending_from or set()
        self._airborne = airborne or set()
        self._progress = progress or {}
        self._targets = targets or {}

    def has_pending_move_from(self, row, col):
        return (row, col) in self._pending_from

    def is_airborne(self, row, col):
        return (row, col) in self._airborne

    def motion_progress(self, row, col):
        return self._progress.get((row, col))

    def motion_target(self, row, col):
        return self._targets.get((row, col))


def make_board(rows):
    return Board(rows)


class TestStaticRendering:
    def test_idle_piece_draws_at_its_cell_position(self):
        board = make_board([["wR", ".", "."]])
        registry = ViewModelRegistry(FakeSpriteLibrary())
        renderer = FakeRenderer()

        registry.render(board, renderer, FakeEngine(), image_w=300, image_h=100, dt_ms=16)

        assert renderer.calls == [("wR/idle/1.png", 0, 0, (100, 100))]


class TestMovingPieceInterpolation:
    def test_draws_halfway_between_source_and_destination_at_50_percent_progress(self):
        board = make_board([["wR", ".", "."]])
        registry = ViewModelRegistry(FakeSpriteLibrary())
        renderer = FakeRenderer()
        engine = FakeEngine(pending_from={(0, 0)}, progress={(0, 0): 0.5}, targets={(0, 0): (0, 2)})

        registry.render(board, renderer, engine, image_w=300, image_h=100, dt_ms=16)

        path, x, y, size = renderer.calls[0]
        assert path == "wR/move/1.png"
        assert x == 100  # halfway between pixel 0 and pixel 200
        assert y == 0

    def test_draws_at_source_when_progress_is_zero(self):
        board = make_board([["wR", ".", "."]])
        registry = ViewModelRegistry(FakeSpriteLibrary())
        renderer = FakeRenderer()
        engine = FakeEngine(pending_from={(0, 0)}, progress={(0, 0): 0.0}, targets={(0, 0): (0, 2)})

        registry.render(board, renderer, engine, image_w=300, image_h=100, dt_ms=16)

        assert renderer.calls[0][1:3] == (0, 0)


class TestArrivalContinuity:
    def test_view_model_relocates_and_keeps_its_move_state_on_arrival(self):
        # Frame 1: piece is mid-move, board still shows it at the source
        # cell (Board doesn't mutate until arrival).
        board_before = make_board([["wR", ".", "."]])
        registry = ViewModelRegistry(FakeSpriteLibrary())
        renderer = FakeRenderer()
        moving_engine = FakeEngine(pending_from={(0, 0)}, progress={(0, 0): 0.9},
                                    targets={(0, 0): (0, 2)})
        registry.render(board_before, renderer, moving_engine, image_w=300, image_h=100, dt_ms=16)
        assert registry.state_name_at(0, 0) == "move"

        # Frame 2: the motion has resolved - board now shows the piece at
        # the destination, and the engine no longer reports a pending
        # move anywhere. A naive fresh-lookup would start a brand new
        # "idle" view model at (0, 2); instead the same view model (still
        # carrying its "move" state) must relocate there and hand off to
        # "long_rest" - not restart at "idle".
        board_after = make_board([[".", ".", "wR"]])
        arrived_engine = FakeEngine()
        registry.render(board_after, renderer, arrived_engine, image_w=300, image_h=100, dt_ms=16)

        assert registry.state_name_at(0, 2) == "long_rest"
        assert registry.state_name_at(0, 0) is None  # nothing left tracked at the old cell


class TestStaleViewModelIsDiscarded:
    def test_a_different_piece_landing_on_a_stale_cell_gets_its_own_fresh_sprite(self):
        # wR at (0,0) is captured (vanishes from the board, no motion
        # involved from the registry's perspective - e.g. an enemy
        # motion resolved and overwrote it). A completely different
        # piece, bN, later ends up on that same cell via some other,
        # unrelated route. The stale wR view model must not be reused
        # for bN.
        registry = ViewModelRegistry(FakeSpriteLibrary())
        renderer = FakeRenderer()

        board_with_rook = make_board([["wR"]])
        registry.render(board_with_rook, renderer, FakeEngine(), image_w=100, image_h=100, dt_ms=16)
        assert renderer.calls[-1][0] == "wR/idle/1.png"

        board_with_knight = make_board([["bN"]])
        registry.render(board_with_knight, renderer, FakeEngine(), image_w=100, image_h=100, dt_ms=16)
        assert renderer.calls[-1][0] == "bN/idle/1.png"

    def test_an_emptied_cell_does_not_linger_and_corrupt_a_later_arrival(self):
        registry = ViewModelRegistry(FakeSpriteLibrary())
        renderer = FakeRenderer()

        board = make_board([["wR", "."]])
        registry.render(board, renderer, FakeEngine(), image_w=200, image_h=100, dt_ms=16)

        # wR is captured/removed with no in-flight motion at all (e.g. an
        # airborne kill, or any other path the registry doesn't
        # explicitly model) - the cell just becomes empty.
        board.set_cell(0, 0, None)
        board.set_cell(0, 1, None)
        registry.render(board, renderer, FakeEngine(), image_w=200, image_h=100, dt_ms=16)

        # A different piece now arrives at that same cell.
        board.set_cell(0, 0, None)
        board_next = make_board([["bQ", "."]])
        registry.render(board_next, renderer, FakeEngine(), image_w=200, image_h=100, dt_ms=16)
        assert renderer.calls[-1][0] == "bQ/idle/1.png"
