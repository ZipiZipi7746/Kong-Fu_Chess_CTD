from kungfu_chess.model.board import Board
from kungfu_chess.model.board_topology import RectangularTopology


def make_simple_board():
    return Board([
        ["bK", ".", "."],
        [".", "wP", "."],
        [".", ".", "wK"],
    ])


class TestInit:
    def test_parses_tokens_into_pieces(self):
        board = make_simple_board()
        assert board.get_cell(0, 0).color == "b"
        assert board.get_cell(0, 0).kind == "K"
        assert board.get_cell(1, 1).color == "w"
        assert board.get_cell(1, 1).kind == "P"

    def test_dot_tokens_become_none(self):
        board = make_simple_board()
        assert board.get_cell(0, 1) is None
        assert board.get_cell(0, 2) is None

    def test_rows_and_cols_computed(self):
        board = make_simple_board()
        assert board.rows == 3
        assert board.cols == 3

    def test_empty_cells_gives_zero_rows_and_cols(self):
        board = Board([])
        assert board.rows == 0
        assert board.cols == 0


class TestIsInside:
    # TODO(test): get_cell/set_cell currently rely entirely on callers
    # checking is_inside first (see the TODO in board.py) - there is no
    # test here today for what get_cell/set_cell themselves do with an
    # out-of-range (row, col) (currently: a plain IndexError from the
    # underlying list, uncontrolled). If/when a validated accessor with
    # an explicit domain exception is introduced, boundary tests
    # asserting that exact exception (rather than today's incidental
    # IndexError) belong here.

    def test_inside_bounds_true(self):
        board = make_simple_board()
        assert board.is_inside(0, 0) is True
        assert board.is_inside(2, 2) is True

    def test_negative_row_or_col_false(self):
        board = make_simple_board()
        assert board.is_inside(-1, 0) is False
        assert board.is_inside(0, -1) is False

    def test_row_or_col_beyond_bounds_false(self):
        board = make_simple_board()
        assert board.is_inside(3, 0) is False
        assert board.is_inside(0, 3) is False


class TestTopologyInjection:
    def test_default_topology_is_rectangular_matching_the_board_shape(self):
        board = make_simple_board()
        assert isinstance(board.topology, RectangularTopology)
        assert board.topology.rows == 3
        assert board.topology.cols == 3

    def test_is_inside_delegates_to_the_default_topology(self):
        board = make_simple_board()
        assert board.is_inside(0, 0) is True
        assert board.is_inside(2, 2) is True
        assert board.is_inside(3, 0) is False
        assert board.is_inside(-1, 0) is False

    def test_is_inside_delegates_to_an_injected_topology(self):
        # An extreme fake to prove is_inside genuinely asks the injected
        # topology rather than still checking rows/cols itself: it
        # rejects a cell the default rectangular topology would accept.
        class AlwaysOutsideTopology:
            def contains(self, row, col):
                return False

        board = Board([["wR", "."]], topology=AlwaysOutsideTopology())
        assert board.is_inside(0, 0) is False

    def test_an_injected_topology_can_also_accept_cells_a_rectangle_would_reject(self):
        class EverySquareTopology:
            def contains(self, row, col):
                return True

        board = Board([["wR"]], topology=EverySquareTopology())
        assert board.is_inside(99, 99) is True


class TestSetCell:
    def test_set_cell_updates_grid(self):
        board = make_simple_board()
        new_piece = board.get_cell(1, 1)
        board.set_cell(0, 1, new_piece)
        board.set_cell(1, 1, None)
        assert board.get_cell(0, 1) is new_piece
        assert board.get_cell(1, 1) is None


class TestIterRows:
    def test_yields_one_tuple_per_row_matching_get_cell(self):
        board = make_simple_board()
        rows = list(board.iter_rows())
        assert len(rows) == board.rows
        for row_index, row in enumerate(rows):
            assert tuple(row) == tuple(
                board.get_cell(row_index, col) for col in range(board.cols))

    def test_rows_are_tuples_not_the_live_list(self):
        # A read-only view (Tell, Don't Ask): mutating what iter_rows()
        # yields must not be possible to route back into the board -
        # only set_cell can change board state.
        board = make_simple_board()
        first_row = next(iter(board.iter_rows()))
        assert isinstance(first_row, tuple)

    def test_reflects_mutations_made_via_set_cell(self):
        board = make_simple_board()
        board.set_cell(0, 1, board.get_cell(0, 0))
        rows = list(board.iter_rows())
        assert rows[0][1] is board.get_cell(0, 0)
