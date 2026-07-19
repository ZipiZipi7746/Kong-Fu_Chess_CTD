class PieceRule:
    """Strategy base class (Rule 6): evaluates whether a piece can legally
    move from one cell to another.

    matches(dr, dc) is the narrow, original hook: pure movement *shape*,
    independent of board state, color or capture. Most pieces are fully
    described by shape alone, so is_legal() (the Template Method every
    rule is actually invoked through) has a default implementation that
    just measures the delta and delegates to matches(). requires_clear_path
    tells RuleEngine whether it also needs to walk the intermediate cells
    for this rule (Information Expert: the rule itself knows whether it
    slides).

    A rule whose legality genuinely depends on more than shape (color,
    absolute position, board occupancy - i.e. Pawn) overrides is_legal()
    directly instead of matches(), and RuleEngine never needs to know the
    difference: every kind in PIECE_RULES is looked up and invoked the
    same way (Liskov Substitution, Open/Closed for future context-
    sensitive pieces).

    This Template Method is a pragmatic *current* solution, not the
    final extensible contract: it was chosen specifically because it
    removes the piece.kind == "P" branch from RuleEngine while touching
    zero already-stable rule classes (see the design-dilemmas write-up
    for the full trade-off). But is_legal()'s default implementation
    still computes dr/dc and calls matches(self, dr, dc) - and dr/dc
    (a rectangular-grid delta) is exactly as grid-specific as it always
    was. A genuinely topology-independent rule contract - e.g.
    is_legal(self, context: RuleContext), where context carries the
    piece, source/destination positions, board, topology, game state and
    clock rather than two integers - is still a required future step,
    not something this refactor already provides.
    """

    requires_clear_path = False

    def matches(self, dr, dc):
        raise NotImplementedError

    # TODO(design): dr/dc here are a rectangular-grid delta - this
    # default implementation, and every non-Pawn rule's matches(), is
    # still bound to "distance measured on a grid". A future rule may
    # need to depend on board contents, topology/connectivity, piece
    # state, cooldown, time, zone, previous actions, or a multi-stage
    # movement - none of which fit through (dr, dc). The eventual
    # topology-independent contract (RuleContext, see this class's
    # docstring) would replace is_legal's signature project-wide, not
    # just add a new parameter here - a cross-cutting change on the same
    # scale as the Position/BoardTopology work, and deliberately staged
    # after those settle rather than guessed at first.
    def is_legal(self, piece, from_row, from_col, to_row, to_col, board):
        dr = abs(to_row - from_row)
        dc = abs(to_col - from_col)
        return self.matches(dr, dc)


class KingRule(PieceRule):
    def matches(self, dr, dc):
        return dr <= 1 and dc <= 1


class RookRule(PieceRule):
    requires_clear_path = True

    def matches(self, dr, dc):
        return (dr == 0) != (dc == 0)


class BishopRule(PieceRule):
    requires_clear_path = True

    def matches(self, dr, dc):
        return dr == dc and dr != 0


class QueenRule(PieceRule):
    requires_clear_path = True

    def __init__(self):
        self._rook = RookRule()
        self._bishop = BishopRule()

    def matches(self, dr, dc):
        return self._rook.matches(dr, dc) or self._bishop.matches(dr, dc)


class KnightRule(PieceRule):
    def matches(self, dr, dc):
        return (dr, dc) in [(2, 1), (1, 2)]


class PawnRule(PieceRule):
    """Pawn's legality depends on color/direction/capture-vs-empty-square,
    not just (dr, dc) shape, so it overrides is_legal() directly rather
    than implementing matches() (which stays unimplemented here, same as
    the base class - nothing calls it for this rule). Moved here from
    RuleEngine's former _pawn_is_legal, unchanged in behavior."""

    def matches(self, dr, dc):
        raise NotImplementedError

    def is_legal(self, piece, from_row, from_col, to_row, to_col, board):
        color = piece.color
        direction = -1 if color == "w" else 1
        start_row = board.rows - 2 if color == "w" else 1

        row_delta = to_row - from_row
        col_delta = to_col - from_col

        destination = board.get_cell(to_row, to_col)

        # One step forward
        if col_delta == 0 and row_delta == direction:
            return destination is None

        # Two steps from starting row
        if (
            col_delta == 0
            and row_delta == 2 * direction
            and from_row == start_row
            and destination is None
        ):
            middle_row = from_row + direction
            return board.get_cell(middle_row, from_col) is None

        # Diagonal capture
        if abs(col_delta) == 1 and row_delta == direction:
            return destination is not None and destination.color != color

        return False


# Registry used by RuleEngine to look up the Strategy for a given piece
# kind - every kind, including Pawn, is invoked the same way via
# is_legal() (see PieceRule's docstring for why Pawn can join this
# registry despite not implementing matches()).
PIECE_RULES = {
    "K": KingRule(),
    "R": RookRule(),
    "B": BishopRule(),
    "Q": QueenRule(),
    "N": KnightRule(),
    "P": PawnRule(),
}
