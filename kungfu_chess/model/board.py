from kungfu_chess.model.piece import Piece


class Board:
    """Pure logic Model: the grid of Pieces and cell access.

    Deliberately has NO rendering/printing method on it (Rule 3 - SoC):
    the Model must be completely decoupled from the View. See
    board_view.BoardRenderer for the View Adapter that reads this model.

    Internal storage (_cells) is private; external callers read it
    through get_cell/set_cell or the read-only iter_rows() (Tell, Don't
    Ask) - this keeps the single-writer convention (only GameEngine ever
    calls set_cell) enforced rather than merely conventional.
    """

    # TODO(design): Every (row, col) is passed around as two loose
    # integers - here and throughout Motion, RealTimeArbiter, GameEngine,
    # RuleEngine, MoveResolvedEvent and the GUI layer. An immutable
    # Position value object (row, col) would prevent row/col argument-
    # order mistakes, shrink method signatures, and centralize equality/
    # bounds-related behavior in one place (Value Object / DDD, avoids
    # Primitive Obsession). Deferred: this would touch method signatures
    # across most layers for a purely structural benefit - a large,
    # cross-cutting change with no behavior difference, better done as
    # its own deliberate, test-driven pass rather than alongside
    # unrelated work.
    def __init__(self, cells):
        self._cells = [[Piece.parse(token) for token in row] for row in cells]
        self.rows = len(self._cells)
        self.cols = len(self._cells[0]) if self._cells else 0

    def is_inside(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols

    # TODO(design): get_cell/set_cell trust the caller to have already
    # checked is_inside - GameController does, before ever calling
    # get_cell with a click-derived cell, but GameEngine and RuleEngine
    # call get_cell/set_cell freely without re-checking, relying on
    # RuleEngine's shape rules and the controller's upstream validation
    # to guarantee in-bounds coordinates. A validated public accessor
    # (raising a domain-specific exception on out-of-range access) with a
    # separate fast/unchecked internal path would centralize boundary
    # enforcement instead of leaving it as an implicit, spread-out
    # contract (Design by Contract, Fail Fast); a Position value object
    # (see above) would be a natural place to own that check. Not added
    # now: no out-of-range access has ever actually occurred here, since
    # every caller today is already constrained upstream (click mapping,
    # rule-validated deltas).
    def get_cell(self, row, col):
        return self._cells[row][col]

    def set_cell(self, row, col, value):
        self._cells[row][col] = value

    def iter_rows(self):
        """Read-only iteration over the grid, row by row - the sanctioned
        way for external callers (e.g. BoardRenderer) to inspect the
        whole board without touching internal storage directly. Each row
        is a tuple (not the live list), so callers can't mutate cells
        through it - only set_cell can."""
        return (tuple(row) for row in self._cells)

    # TODO(design): Board has no way to copy or snapshot its current
    # state. A Memento-style immutable snapshot (or a cheap copy-on-write
    # clone) would enable undo, move replay, AI search (trying a move and
    # rolling it back), or speculative "what if" analysis without
    # mutating the live game. Not needed for this iteration: the current
    # game has no undo/replay/AI requirement, so this would be
    # speculative infrastructure with no consumer yet.
