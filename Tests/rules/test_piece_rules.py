import pytest

from kungfu_chess.rules.piece_rules import (
    PieceRule,
    KingRule,
    RookRule,
    BishopRule,
    QueenRule,
    KnightRule,
    PIECE_RULES,
)


class TestPieceRuleBase:
    def test_matches_not_implemented(self):
        with pytest.raises(NotImplementedError):
            PieceRule().matches(1, 1)

    # TODO(test): If PieceRule.matches() is widened to a full-context
    # signature (see the TODO in piece_rules.py) and Pawn joins this
    # Strategy family as PawnRule, a shared parametrized contract test
    # (iterating PIECE_RULES.values() plus PawnRule, asserting each
    # returns a bool and never raises for arbitrary valid inputs) would
    # guard that every implementation still satisfies the same interface
    # - useful once there is more than a fixed five-rule set to keep in
    # sync by hand.


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


class TestPieceRulesRegistry:
    def test_all_non_pawn_kinds_present(self):
        for kind in ("K", "R", "B", "Q", "N"):
            assert kind in PIECE_RULES

    def test_pawn_deliberately_excluded(self):
        assert "P" not in PIECE_RULES
