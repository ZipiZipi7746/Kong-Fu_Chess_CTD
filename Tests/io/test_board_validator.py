import pytest

from kungfu_chess.io.board_validator import BoardValidator
from kungfu_chess.model.exceptions import RowWidthMismatch, UnknownToken
from kungfu_chess.rules.piece_rules import PIECE_RULES


class TestValidateRowWidth:
    def test_empty_board_rows_is_fine(self):
        BoardValidator.validate_row_width([])

    def test_consistent_width_is_fine(self):
        BoardValidator.validate_row_width([["wR", "."], [".", "bK"]])

    def test_inconsistent_width_raises(self):
        with pytest.raises(RowWidthMismatch):
            BoardValidator.validate_row_width([["wR", "."], ["."]])


class TestValidateTokens:
    def test_dot_token_is_fine(self):
        BoardValidator.validate_tokens([["."]])

    def test_valid_piece_and_color_is_fine(self):
        BoardValidator.validate_tokens([["wK", "bQ", "wP", "bR", "wN", "bB"]])

    def test_wrong_length_token_raises(self):
        with pytest.raises(UnknownToken):
            BoardValidator.validate_tokens([["wKK"]])

    def test_invalid_color_raises(self):
        with pytest.raises(UnknownToken):
            BoardValidator.validate_tokens([["xK"]])

    def test_invalid_piece_raises(self):
        with pytest.raises(UnknownToken):
            BoardValidator.validate_tokens([["wZ"]])


class TestValidate:
    def test_valid_board_passes_both_checks(self):
        BoardValidator.validate([["wR", "."], [".", "bK"]])

    def test_row_width_error_takes_precedence(self):
        with pytest.raises(RowWidthMismatch):
            BoardValidator.validate([["wR", "."], ["wZ"]])


class TestValidTokenRegistryInjection:
    def test_default_valid_piece_kinds_matches_the_real_rule_registry(self):
        # Single Source of Truth: the default isn't a second, separately
        # maintained set of letters - it's the same PIECE_RULES keys
        # RuleEngine already dispatches through.
        for kind in PIECE_RULES:
            BoardValidator.validate_tokens([[f"w{kind}"]])

    def test_injected_registry_rejects_a_kind_the_real_one_allows(self):
        with pytest.raises(UnknownToken):
            BoardValidator.validate_tokens([["wK"]], valid_piece_kinds={"Q"})

    def test_injected_registry_accepts_a_kind_the_real_one_does_not(self):
        # Proves validate_tokens genuinely consults the injected set
        # rather than falling back to the real PIECE_RULES underneath.
        BoardValidator.validate_tokens([["wZ"]], valid_piece_kinds={"Z"})

    def test_validate_forwards_the_injected_registry_to_validate_tokens(self):
        with pytest.raises(UnknownToken):
            BoardValidator.validate([["wK"]], valid_piece_kinds={"Q"})
