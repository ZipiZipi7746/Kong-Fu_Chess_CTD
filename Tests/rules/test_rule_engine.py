from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.rules.rule_engine import RuleEngine


def board_from_rows(rows):
    return Board(rows)


# TODO(test): If PIECE_RULES is ever injected through RuleEngine's
# constructor instead of imported as a module global (see the TODO in
# rule_engine.py), a test constructing RuleEngine(rule_registry={...a
# minimal fake...}) and asserting is_legal() consults the injected
# registry rather than the real PIECE_RULES would prove that seam
# actually works, the same way GameEngine's injected-arbiter/rule_engine
# tests do today.
class TestIsLegalGeneral:
    def test_same_from_and_to_cell_is_illegal(self):
        board = board_from_rows([["wR", "."], [".", "."]])
        engine = RuleEngine()
        rook = board.get_cell(0, 0)
        assert engine.is_legal(rook, 0, 0, 0, 0, board) is False

    def test_unknown_piece_kind_is_illegal(self):
        board = board_from_rows([[".", "."], [".", "."]])
        engine = RuleEngine()
        mystery = Piece("w", "X")
        assert engine.is_legal(mystery, 0, 0, 1, 1, board) is False

    def test_cannot_capture_own_color(self):
        board = board_from_rows([
            ["wR", ".", "wR"],
            [".", ".", "."],
            [".", ".", "."],
        ])
        engine = RuleEngine()
        rook = board.get_cell(0, 0)
        assert engine.is_legal(rook, 0, 0, 0, 2, board) is False

    def test_can_capture_opposite_color(self):
        board = board_from_rows([
            ["wR", ".", "bR"],
            [".", ".", "."],
            [".", ".", "."],
        ])
        engine = RuleEngine()
        rook = board.get_cell(0, 0)
        assert engine.is_legal(rook, 0, 0, 0, 2, board) is True


class TestKingKnightMoves:
    def test_king_one_step_is_legal(self):
        board = board_from_rows([["wK", "."], [".", "."]])
        engine = RuleEngine()
        king = board.get_cell(0, 0)
        assert engine.is_legal(king, 0, 0, 0, 1, board) is True

    def test_king_two_steps_is_illegal(self):
        board = board_from_rows([["wK", ".", "."]])
        engine = RuleEngine()
        king = board.get_cell(0, 0)
        assert engine.is_legal(king, 0, 0, 0, 2, board) is False

    def test_knight_l_shape_is_legal(self):
        board = board_from_rows([
            ["wN", ".", "."],
            [".", ".", "."],
            [".", ".", "."],
        ])
        engine = RuleEngine()
        knight = board.get_cell(0, 0)
        assert engine.is_legal(knight, 0, 0, 2, 1, board) is True

    def test_knight_non_l_shape_is_illegal(self):
        board = board_from_rows([
            ["wN", ".", "."],
            [".", ".", "."],
            [".", ".", "."],
        ])
        engine = RuleEngine()
        knight = board.get_cell(0, 0)
        assert engine.is_legal(knight, 0, 0, 1, 1, board) is False


class TestSlidingPieces:
    def test_rook_clear_path_is_legal(self):
        board = board_from_rows([["wR", ".", "."]])
        engine = RuleEngine()
        rook = board.get_cell(0, 0)
        assert engine.is_legal(rook, 0, 0, 0, 2, board) is True

    def test_rook_blocked_path_is_illegal(self):
        board = board_from_rows([["wR", "wP", "."]])
        engine = RuleEngine()
        rook = board.get_cell(0, 0)
        assert engine.is_legal(rook, 0, 0, 0, 2, board) is False

    def test_bishop_clear_diagonal_is_legal(self):
        board = board_from_rows([
            ["wB", ".", "."],
            [".", ".", "."],
            [".", ".", "."],
        ])
        engine = RuleEngine()
        bishop = board.get_cell(0, 0)
        assert engine.is_legal(bishop, 0, 0, 2, 2, board) is True

    def test_bishop_blocked_diagonal_is_illegal(self):
        board = board_from_rows([
            ["wB", ".", "."],
            [".", "wP", "."],
            [".", ".", "."],
        ])
        engine = RuleEngine()
        bishop = board.get_cell(0, 0)
        assert engine.is_legal(bishop, 0, 0, 2, 2, board) is False

    def test_queen_moves_like_rook(self):
        board = board_from_rows([["wQ", ".", "."]])
        engine = RuleEngine()
        queen = board.get_cell(0, 0)
        assert engine.is_legal(queen, 0, 0, 0, 2, board) is True

    def test_queen_moves_like_bishop(self):
        board = board_from_rows([
            ["wQ", ".", "."],
            [".", ".", "."],
            [".", ".", "."],
        ])
        engine = RuleEngine()
        queen = board.get_cell(0, 0)
        assert engine.is_legal(queen, 0, 0, 2, 2, board) is True

    def test_path_clear_upward_and_leftward_directions(self):
        # Exercises negative row_step / col_step branches of _sign via a
        # rook moving up-and-to-the-left along a clear diagonal-adjacent
        # straight line (down/right occupied differently from up/left).
        board = board_from_rows([
            [".", ".", "."],
            [".", ".", "."],
            [".", ".", "wR"],
        ])
        engine = RuleEngine()
        rook = board.get_cell(2, 2)
        assert engine.is_legal(rook, 2, 2, 0, 2, board) is True
        assert engine.is_legal(rook, 2, 2, 2, 0, board) is True


class TestPawnMoves:
    def test_one_step_forward_onto_empty_is_legal_white(self):
        board = board_from_rows([["."], ["wP"], ["."]])
        engine = RuleEngine()
        pawn = board.get_cell(1, 0)
        assert engine.is_legal(pawn, 1, 0, 0, 0, board) is True

    def test_one_step_forward_onto_occupied_is_illegal_white(self):
        board = board_from_rows([["bP"], ["wP"], ["."]])
        engine = RuleEngine()
        pawn = board.get_cell(1, 0)
        assert engine.is_legal(pawn, 1, 0, 0, 0, board) is False

    def test_one_step_forward_black_direction(self):
        board = board_from_rows([["."], ["bP"], ["."]])
        engine = RuleEngine()
        pawn = board.get_cell(1, 0)
        assert engine.is_legal(pawn, 1, 0, 2, 0, board) is True

    def test_two_steps_from_start_row_white(self):
        # White pawn's starting rank is one row in from the back rank
        # (board.rows - 2), matching real chess starting position.
        rows = [["."] for _ in range(4)]
        rows[2] = ["wP"]
        board = board_from_rows(rows)
        engine = RuleEngine()
        pawn = board.get_cell(2, 0)
        assert engine.is_legal(pawn, 2, 0, 0, 0, board) is True

    def test_two_steps_from_back_rank_is_illegal(self):
        # A pawn sitting on the very back rank (not the actual starting
        # rank) must not be allowed a two-step advance.
        rows = [["."] for _ in range(4)]
        rows[3] = ["wP"]
        board = board_from_rows(rows)
        engine = RuleEngine()
        pawn = board.get_cell(3, 0)
        assert engine.is_legal(pawn, 3, 0, 1, 0, board) is False

    def test_two_steps_blocked_by_middle_piece(self):
        rows = [["."] for _ in range(4)]
        rows[2] = ["wP"]
        rows[1] = ["wP"]
        board = board_from_rows(rows)
        engine = RuleEngine()
        pawn = board.get_cell(2, 0)
        assert engine.is_legal(pawn, 2, 0, 0, 0, board) is False

    def test_two_steps_blocked_by_destination_piece(self):
        rows = [["."] for _ in range(4)]
        rows[2] = ["wP"]
        rows[0] = ["bP"]
        board = board_from_rows(rows)
        engine = RuleEngine()
        pawn = board.get_cell(2, 0)
        assert engine.is_legal(pawn, 2, 0, 0, 0, board) is False

    def test_two_steps_from_start_row_black(self):
        # Black's starting rank is row index 1 (one row in from the top
        # back rank), mirroring white's board.rows - 2.
        rows = [["."] for _ in range(4)]
        rows[1] = ["bP"]
        board = board_from_rows(rows)
        engine = RuleEngine()
        pawn = board.get_cell(1, 0)
        assert engine.is_legal(pawn, 1, 0, 3, 0, board) is True

    def test_two_steps_not_from_start_row_is_illegal(self):
        rows = [["."] for _ in range(5)]
        rows[2] = ["wP"]
        board = board_from_rows(rows)
        engine = RuleEngine()
        pawn = board.get_cell(2, 0)
        assert engine.is_legal(pawn, 2, 0, 0, 0, board) is False

    def test_diagonal_capture_is_legal(self):
        board = board_from_rows([
            [".", "bP", "."],
            ["wP", ".", "."],
        ])
        engine = RuleEngine()
        pawn = board.get_cell(1, 0)
        assert engine.is_legal(pawn, 1, 0, 0, 1, board) is True

    def test_diagonal_without_capture_is_illegal(self):
        board = board_from_rows([
            [".", ".", "."],
            ["wP", ".", "."],
        ])
        engine = RuleEngine()
        pawn = board.get_cell(1, 0)
        assert engine.is_legal(pawn, 1, 0, 0, 1, board) is False

    def test_diagonal_capture_of_own_color_is_illegal(self):
        board = board_from_rows([
            [".", "wP", "."],
            ["wP", ".", "."],
        ])
        engine = RuleEngine()
        pawn = board.get_cell(1, 0)
        assert engine.is_legal(pawn, 1, 0, 0, 1, board) is False

    def test_sideways_move_is_illegal(self):
        board = board_from_rows([["wP", "."]])
        engine = RuleEngine()
        pawn = board.get_cell(0, 0)
        assert engine.is_legal(pawn, 0, 0, 0, 1, board) is False

    def test_backwards_move_is_illegal(self):
        board = board_from_rows([["."], ["wP"], ["."]])
        engine = RuleEngine()
        pawn = board.get_cell(1, 0)
        assert engine.is_legal(pawn, 1, 0, 2, 0, board) is False
