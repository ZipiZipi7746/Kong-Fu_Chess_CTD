from src.domain.board import Board


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


class TestSetCell:
    def test_set_cell_updates_grid(self):
        board = make_simple_board()
        new_piece = board.get_cell(1, 1)
        board.set_cell(0, 1, new_piece)
        board.set_cell(1, 1, None)
        assert board.get_cell(0, 1) is new_piece
        assert board.get_cell(1, 1) is None
