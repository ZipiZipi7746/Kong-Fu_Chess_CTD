from kungfu_chess.model.piece import Piece


class PromotionRule:
    """Dedicated strategy/sub-service (Rule 6) for pawn promotion.
    Resolves whether a piece that just arrived at its destination should
    be promoted, and returns the resulting piece. Called by GameEngine
    upon Motion arrival (Rule 8).
    """

    # TODO(design): The promotion target ("Q") is hardcoded here, and the
    # promotion rows are standard-chess assumptions (row 0 for White, the
    # last row for Black). Injecting the promotion kind/rows (or sourcing
    # them from a future PieceDefinition registry, see the TODO on
    # Piece.kind) would let a variant configure "promote to Queen only"
    # vs. player-choice promotion, or a differently-shaped board, without
    # editing this class (Strategy Pattern, configuration over hard
    # coding, Open/Closed). Left hardcoded for this iteration: standard
    # chess promotion is the only rule this project needs right now, and
    # configurability would be speculative until a variant requires it.
    @staticmethod
    def resolve(piece, to_row, board):
        if piece.color == "w" and piece.is_pawn() and to_row == 0:
            return Piece("w", "Q")
        if piece.color == "b" and piece.is_pawn() and to_row == board.rows - 1:
            return Piece("b", "Q")
        return piece
