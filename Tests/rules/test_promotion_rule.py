from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.rules.promotion_rule import PromotionRule


def make_board(rows=8):
    return Board([["."] * 1 for _ in range(rows)])


class TestResolve:
    def test_white_pawn_reaching_row_zero_promotes_to_queen(self):
        board = make_board()
        pawn = Piece("w", "P")
        result = PromotionRule.resolve(pawn, 0, board)
        assert result == Piece("w", "Q")

    def test_black_pawn_reaching_last_row_promotes_to_queen(self):
        board = make_board(rows=8)
        pawn = Piece("b", "P")
        result = PromotionRule.resolve(pawn, board.rows - 1, board)
        assert result == Piece("b", "Q")

    def test_white_pawn_not_at_row_zero_does_not_promote(self):
        board = make_board()
        pawn = Piece("w", "P")
        result = PromotionRule.resolve(pawn, 3, board)
        assert result is pawn

    def test_black_pawn_not_at_last_row_does_not_promote(self):
        board = make_board()
        pawn = Piece("b", "P")
        result = PromotionRule.resolve(pawn, 3, board)
        assert result is pawn

    def test_non_pawn_piece_never_promotes(self):
        board = make_board()
        rook = Piece("w", "R")
        result = PromotionRule.resolve(rook, 0, board)
        assert result is rook

    def test_black_pawn_at_row_zero_does_not_promote(self):
        # Row zero is white's promotion row only.
        board = make_board()
        pawn = Piece("b", "P")
        result = PromotionRule.resolve(pawn, 0, board)
        assert result is pawn

    def test_white_pawn_at_last_row_does_not_promote(self):
        # Last row is black's promotion row only.
        board = make_board()
        pawn = Piece("w", "P")
        result = PromotionRule.resolve(pawn, board.rows - 1, board)
        assert result is pawn

    def test_promotion_kind_defaults_to_queen(self):
        assert PromotionRule.DEFAULT_PROMOTION_KIND == "Q"

    def test_explicit_promotion_kind_overrides_the_default(self):
        board = make_board()
        pawn = Piece("w", "P")
        result = PromotionRule.resolve(pawn, 0, board, promotion_kind="N")
        assert result == Piece("w", "N")

    def test_explicit_promotion_kind_has_no_effect_when_not_promoting(self):
        board = make_board()
        pawn = Piece("w", "P")
        result = PromotionRule.resolve(pawn, 3, board, promotion_kind="N")
        assert result is pawn
