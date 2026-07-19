from kungfu_chess.model.exceptions import (
    GameInputError,
    BoardParsingError,
    UnknownToken,
    RowWidthMismatch,
)


class TestExceptionTypes:
    def test_unknown_token_is_a_value_error(self):
        assert issubclass(UnknownToken, ValueError)

    def test_row_width_mismatch_is_a_value_error(self):
        assert issubclass(RowWidthMismatch, ValueError)

    def test_unknown_token_carries_message(self):
        try:
            raise UnknownToken("UNKNOWN_TOKEN")
        except UnknownToken as e:
            assert str(e) == "UNKNOWN_TOKEN"

    def test_row_width_mismatch_carries_message(self):
        try:
            raise RowWidthMismatch("ROW_WIDTH_MISMATCH")
        except RowWidthMismatch as e:
            assert str(e) == "ROW_WIDTH_MISMATCH"


class TestExceptionHierarchy:
    def test_game_input_error_is_a_value_error(self):
        assert issubclass(GameInputError, ValueError)

    def test_board_parsing_error_is_a_game_input_error(self):
        assert issubclass(BoardParsingError, GameInputError)

    def test_unknown_token_is_a_board_parsing_error(self):
        assert issubclass(UnknownToken, BoardParsingError)

    def test_row_width_mismatch_is_a_board_parsing_error(self):
        assert issubclass(RowWidthMismatch, BoardParsingError)

    def test_both_are_catchable_as_a_single_game_input_error(self):
        for exc_type in (UnknownToken, RowWidthMismatch):
            try:
                raise exc_type("boom")
            except GameInputError:
                pass
            else:
                raise AssertionError(f"{exc_type} was not caught as GameInputError")

    def test_an_unrelated_value_error_is_not_a_game_input_error(self):
        assert not isinstance(ValueError("unrelated"), GameInputError)
