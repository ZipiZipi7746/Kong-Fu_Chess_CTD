from exceptions import RowWidthMismatch, UnknownToken

VALID_PIECES = {"K", "Q", "R", "B", "N", "P"}
VALID_COLORS = {"w", "b"}


class BoardValidator:

    @staticmethod
    def validate(board_rows):
        BoardValidator.validate_row_width(board_rows)
        BoardValidator.validate_tokens(board_rows)

    @staticmethod
    def validate_row_width(board_rows):
        if not board_rows:
            return

        width = len(board_rows[0])

        for row in board_rows:
            if len(row) != width:
                raise RowWidthMismatch("ROW_WIDTH_MISMATCH")

    @staticmethod
    def validate_tokens(board_rows):
        for row in board_rows:
            for token in row:

                if token == ".":
                    continue

                if len(token) != 2:
                    raise UnknownToken("UNKNOWN_TOKEN")

                color = token[0]
                piece = token[1]

                if color not in VALID_COLORS or piece not in VALID_PIECES:
                    raise UnknownToken("UNKNOWN_TOKEN")
