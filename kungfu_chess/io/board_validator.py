from kungfu_chess.model.exceptions import RowWidthMismatch, UnknownToken
from kungfu_chess.rules.piece_rules import PIECE_RULES

VALID_COLORS = {"w", "b"}


class BoardValidator:
    """valid_piece_kinds is an optional Dependency Injection point,
    defaulting to PIECE_RULES.keys() - the same registry RuleEngine
    dispatches through (Single Source of Truth: a board-text validator
    and a rules engine agreeing on "which piece kinds exist" by
    construction, rather than each keeping its own separately maintained
    list that could drift out of sync)."""

    @staticmethod
    def validate(board_rows, valid_piece_kinds=None):
        BoardValidator.validate_row_width(board_rows)
        BoardValidator.validate_tokens(board_rows, valid_piece_kinds)

    # TODO(design): validate_row_width requires every row to share
    # exactly one width - a rectangular-board assumption baked directly
    # into board text validation. An irregular topology (holes, uneven
    # rows) would need this relaxed or replaced by asking a BoardTopology
    # (see model/board_topology.py) whether the parsed shape is valid,
    # rather than a fixed "all rows equal length" rule. Not changed now:
    # no irregular board format exists yet to validate against, and
    # guessing at the future text format without one would be premature.
    @staticmethod
    def validate_row_width(board_rows):
        if not board_rows:
            return

        width = len(board_rows[0])

        for row in board_rows:
            if len(row) != width:
                raise RowWidthMismatch("ROW_WIDTH_MISMATCH")

    @staticmethod
    def validate_tokens(board_rows, valid_piece_kinds=None):
        kinds = valid_piece_kinds if valid_piece_kinds is not None else PIECE_RULES.keys()

        for row in board_rows:
            for token in row:

                if token == ".":
                    continue

                if len(token) != 2:
                    raise UnknownToken("UNKNOWN_TOKEN")

                color = token[0]
                piece = token[1]

                if color not in VALID_COLORS or piece not in kinds:
                    raise UnknownToken("UNKNOWN_TOKEN")
