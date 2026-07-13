from kungfu_chess.model.board import Board
from kungfu_chess.io.board_view import BoardRenderer


class TestToRows:
    def test_pieces_rendered_as_tokens(self):
        board = Board([["wR", "."], [".", "bK"]])
        rows = BoardRenderer.to_rows(board)
        assert rows == [["wR", "."], [".", "bK"]]

    def test_empty_board_gives_empty_rows(self):
        board = Board([])
        assert BoardRenderer.to_rows(board) == []


class TestRender:
    def test_render_prints_space_joined_rows(self, capsys):
        board = Board([["wR", ".", "bK"], [".", "wP", "."]])
        BoardRenderer.render(board)
        captured = capsys.readouterr()
        assert captured.out == "wR . bK\n. wP .\n"

    def test_render_empty_board_prints_nothing(self, capsys):
        board = Board([])
        BoardRenderer.render(board)
        captured = capsys.readouterr()
        assert captured.out == ""
