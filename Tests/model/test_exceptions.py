from kungfu_chess.model.exceptions import UnknownToken, RowWidthMismatch


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
