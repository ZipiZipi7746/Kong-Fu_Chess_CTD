from kungfu_chess.model.piece import Piece


class PromotionRule:
    """Dedicated strategy/sub-service (Rule 6) for pawn promotion.
    Resolves whether a piece that just arrived at its destination should
    be promoted, and returns the resulting piece. Called by GameEngine
    upon Motion arrival (Rule 8).

    The promotion target defaults to Queen (DEFAULT_PROMOTION_KIND),
    matching standard chess, but is an overridable parameter rather than
    an inline literal - a variant needing a different target (or
    eventually player-choice promotion) can pass promotion_kind without
    editing this class (configuration over hard coding, Open/Closed).
    Promotion *rows* are left as standard-chess assumptions (row 0 for
    White, the last row for Black - the latter already derived from
    board.rows rather than hardcoded): this project has no variant with
    a different promotion rank, so parameterizing rows too would be
    speculative until one exists.
    """

    DEFAULT_PROMOTION_KIND = "Q"

    @staticmethod
    def resolve(piece, to_row, board, promotion_kind=None):
        kind = promotion_kind if promotion_kind is not None else PromotionRule.DEFAULT_PROMOTION_KIND
        if piece.color == "w" and piece.is_pawn() and to_row == 0:
            return Piece("w", kind)
        if piece.color == "b" and piece.is_pawn() and to_row == board.rows - 1:
            return Piece("b", kind)
        return piece
