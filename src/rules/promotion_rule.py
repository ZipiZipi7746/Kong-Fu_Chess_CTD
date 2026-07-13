from src.domain.piece import Piece


class PromotionRule:
    """Dedicated strategy/sub-service (Rule 6) for pawn promotion.
    Resolves whether a piece that just arrived at its destination should
    be promoted, and returns the resulting piece. Called by GameEngine
    upon Motion arrival (Rule 8).
    """

    @staticmethod
    def resolve(piece, to_row, board):
        if piece.color == "w" and piece.is_pawn() and to_row == 0:
            return Piece("w", "Q")
        if piece.color == "b" and piece.is_pawn() and to_row == board.rows - 1:
            return Piece("b", "Q")
        return piece
