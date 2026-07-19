import pytest

from kungfu_chess.model.board import Board
from kungfu_chess.rules.piece_rules import (
    PieceRule,
    KingRule,
    RookRule,
    BishopRule,
    QueenRule,
    KnightRule,
    PawnRule,
    PIECE_RULES,
)


class TestPieceRuleBase:
    def test_matches_not_implemented(self):
        with pytest.raises(NotImplementedError):
            PieceRule().matches(1, 1)

    def test_is_legal_default_computes_deltas_and_delegates_to_matches(self):
        # The Template Method every rule is actually invoked through:
        # is_legal() measures (dr, dc) from the raw positions and asks
        # matches() - proven here via a concrete subclass, since the
        # base class's own matches() still just raises.
        rule = KingRule()
        board = Board([["wK", ".", "."]])
        king = board.get_cell(0, 0)
        assert rule.is_legal(king, 0, 0, 0, 1, board) is True
        assert rule.is_legal(king, 0, 0, 0, 2, board) is False


class TestKingRule:
    def test_one_step_any_direction_matches(self):
        rule = KingRule()
        assert rule.matches(1, 0) is True
        assert rule.matches(0, 1) is True
        assert rule.matches(1, 1) is True

    def test_two_or_more_steps_does_not_match(self):
        rule = KingRule()
        assert rule.matches(2, 0) is False
        assert rule.matches(0, 2) is False
        assert rule.matches(2, 2) is False

    def test_does_not_require_a_clear_path(self):
        assert KingRule().requires_clear_path is False


class TestRookRule:
    def test_pure_horizontal_or_vertical_matches(self):
        rule = RookRule()
        assert rule.matches(0, 5) is True
        assert rule.matches(5, 0) is True

    def test_diagonal_does_not_match(self):
        rule = RookRule()
        assert rule.matches(3, 3) is False

    def test_no_movement_does_not_match(self):
        rule = RookRule()
        assert rule.matches(0, 0) is False

    def test_requires_a_clear_path(self):
        assert RookRule().requires_clear_path is True


class TestBishopRule:
    def test_equal_nonzero_deltas_match(self):
        rule = BishopRule()
        assert rule.matches(4, 4) is True

    def test_unequal_deltas_do_not_match(self):
        rule = BishopRule()
        assert rule.matches(2, 3) is False

    def test_zero_delta_does_not_match(self):
        rule = BishopRule()
        assert rule.matches(0, 0) is False

    def test_requires_a_clear_path(self):
        assert BishopRule().requires_clear_path is True


class TestQueenRule:
    def test_rook_like_move_matches(self):
        rule = QueenRule()
        assert rule.matches(0, 6) is True

    def test_bishop_like_move_matches(self):
        rule = QueenRule()
        assert rule.matches(3, 3) is True

    def test_knight_like_move_does_not_match(self):
        rule = QueenRule()
        assert rule.matches(2, 1) is False

    def test_requires_a_clear_path(self):
        assert QueenRule().requires_clear_path is True


class TestKnightRule:
    def test_valid_knight_shapes_match(self):
        rule = KnightRule()
        assert rule.matches(2, 1) is True
        assert rule.matches(1, 2) is True

    def test_invalid_shapes_do_not_match(self):
        rule = KnightRule()
        assert rule.matches(2, 2) is False
        assert rule.matches(1, 1) is False
        assert rule.matches(0, 0) is False

    def test_does_not_require_a_clear_path(self):
        assert KnightRule().requires_clear_path is False


class TestPawnRule:
    """Pawn overrides is_legal() directly rather than matches() (see
    PawnRule's docstring) - exhaustive pawn-legality cases already live
    in Tests/rules/test_rule_engine.py::TestPawnMoves, exercised through
    the public RuleEngine.is_legal API this rule now serves. These are
    just enough to prove the rule itself is polymorphically usable."""

    def test_matches_not_implemented(self):
        with pytest.raises(NotImplementedError):
            PawnRule().matches(1, 0)

    def test_one_step_forward_onto_empty_is_legal(self):
        board = Board([["."], ["wP"], ["."]])
        pawn = board.get_cell(1, 0)
        assert PawnRule().is_legal(pawn, 1, 0, 0, 0, board) is True

    def test_one_step_forward_onto_occupied_is_illegal(self):
        board = Board([["bP"], ["wP"], ["."]])
        pawn = board.get_cell(1, 0)
        assert PawnRule().is_legal(pawn, 1, 0, 0, 0, board) is False

    def test_diagonal_capture_is_legal(self):
        board = Board([[".", "bP", "."], ["wP", ".", "."]])
        pawn = board.get_cell(1, 0)
        assert PawnRule().is_legal(pawn, 1, 0, 0, 1, board) is True

    def test_does_not_require_a_clear_path(self):
        # Pawn's own is_legal already accounts for the single middle
        # square on a two-step advance - it never needs RuleEngine's
        # generic multi-cell path walk.
        assert PawnRule().requires_clear_path is False


class TestPieceRulesRegistry:
    def test_all_kinds_present(self):
        for kind in ("K", "R", "B", "Q", "N", "P"):
            assert kind in PIECE_RULES

    def test_pawn_is_a_full_registry_entry(self):
        # Pawn joins the same Strategy registry as every other kind
        # (see PieceRule's docstring for how it satisfies the interface
        # despite not implementing matches()) - RuleEngine no longer
        # needs a piece.kind == "P" special case to dispatch to it.
        assert isinstance(PIECE_RULES["P"], PawnRule)
