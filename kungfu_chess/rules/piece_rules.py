class PieceRule:
    """Strategy base class (Rule 6): evaluates a piece's theoretical
    movement capability (shape only) independent of board obstruction
    state. Obstruction/path-blocking is handled separately by the
    RuleEngine.
    """

    # TODO(design): matches() only receives (dr, dc) - a delta-only
    # contract. That's why Pawn can't implement this Strategy today: its
    # legality depends on color, absolute from/to position and board
    # occupancy, not just the shape of the move (see RuleEngine's
    # _pawn_is_legal special case). Widening the contract to something
    # like matches(piece, from_row, from_col, to_row, to_col, board)
    # would let PawnRule (and any future context-sensitive piece) satisfy
    # the same Strategy interface as everyone else - removing the
    # type-specific branch in RuleEngine and keeping it Open/Closed for
    # new piece kinds (Liskov Substitution: every PieceRule truly
    # interchangeable). Deferred because today's five rules are pure
    # functions of the delta, and widening the signature only pays off
    # once Pawn (or a future piece) needs to join the same abstraction.
    def matches(self, dr, dc):
        raise NotImplementedError


class KingRule(PieceRule):
    def matches(self, dr, dc):
        return dr <= 1 and dc <= 1


class RookRule(PieceRule):
    def matches(self, dr, dc):
        return (dr == 0) != (dc == 0)


class BishopRule(PieceRule):
    def matches(self, dr, dc):
        return dr == dc and dr != 0


class QueenRule(PieceRule):
    def __init__(self):
        self._rook = RookRule()
        self._bishop = BishopRule()

    def matches(self, dr, dc):
        return self._rook.matches(dr, dc) or self._bishop.matches(dr, dc)


class KnightRule(PieceRule):
    def matches(self, dr, dc):
        return (dr, dc) in [(2, 1), (1, 2)]


# Registry used by RuleEngine to look up the Strategy for a given piece
# kind. Pawn is intentionally excluded: its rule depends on color,
# direction and captures, not just (dr, dc) shape, so it is handled as
# its own case in RuleEngine (mirroring the original design).
PIECE_RULES = {
    "K": KingRule(),
    "R": RookRule(),
    "B": BishopRule(),
    "Q": QueenRule(),
    "N": KnightRule(),
}
