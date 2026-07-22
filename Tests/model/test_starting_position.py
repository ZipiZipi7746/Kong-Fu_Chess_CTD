from kungfu_chess.model.starting_position import standard_starting_board


class TestStandardStartingBoard:
    def test_kings_are_on_their_starting_squares(self):
        board = standard_starting_board()
        assert board.get_cell(0, 4).kind == "K"
        assert board.get_cell(0, 4).color == "b"
        assert board.get_cell(7, 4).kind == "K"
        assert board.get_cell(7, 4).color == "w"

    def test_is_a_standard_eight_by_eight_board(self):
        board = standard_starting_board()
        assert board.rows == 8
        assert board.cols == 8

    def test_each_call_returns_an_independent_board(self):
        first = standard_starting_board()
        second = standard_starting_board()
        first.set_cell(4, 4, None)
        assert second.get_cell(0, 4).kind == "K"  # unaffected by mutating first
