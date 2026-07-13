import pytest

from kungfu_chess.io.board_validator import BoardValidator
from kungfu_chess.model.exceptions import RowWidthMismatch, UnknownToken


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
