from kungfu_chess.model.piece import Piece
from kungfu_chess.model.board_topology import RectangularTopology


class Board:
    """Pure logic Model: the grid of Pieces and cell access.

    Deliberately has NO rendering/printing method on it (Rule 3 - SoC):
    the Model must be completely decoupled from the View. See
    board_view.BoardRenderer for the View Adapter that reads this model.

    Internal storage (_cells) is private; external callers read it
    through get_cell/set_cell or the read-only iter_rows() (Tell, Don't
    Ask) - this keeps the single-writer convention (only GameEngine ever
    calls set_cell) enforced rather than merely conventional.

    topology is an optional Dependency Injection point (Strategy
    Pattern): it answers "does this (row, col) exist" for is_inside,
    defaulting to RectangularTopology(rows, cols) - the current grid
    shape treated as one implementation rather than a permanent
    assumption (see board_topology.py for what a fuller, non-rectangular
    topology would still need beyond this first seam).
    """

    # TODO(design): Every (row, col) is passed around as two loose
    # integers - here and throughout Motion, RealTimeArbiter, GameEngine,
    # RuleEngine, MoveResolvedEvent and the GUI layer. This is Primitive
    # Obsession, and a plain Position(row, col) value object would fix
    # the immediate symptom (argument-order mistakes, equality) - but
    # loose (row, col) is also *how* the whole engine assumes a
    # rectangular grid. A topology-independent variant needs positions
    # that don't have to be integer coordinates at all (a hex axial
    # coordinate, a graph node id, an opaque cell key), so the eventual
    # abstraction is better thought of as a family - Position as the
    # general contract the engine depends on, with GridPosition as
    # today's rectangular implementation and e.g. HexPosition/
    # NodePosition as future ones - rather than a single concrete
    # Position(row, col) class, which would still bake in "a position is
    # two integers" and block exactly the variation this project needs
    # to support (Value Object / DDD, Open/Closed). Required direction,
    # not speculative - but deferred: it touches method signatures
    # across nearly every layer for a purely structural change, and
    # should be its own dedicated, test-driven pass once BoardTopology
    # (see below) has proven out which shape the abstraction needs to
    # take, rather than guessed at in isolation.
    def __init__(self, cells, topology=None):
        self._cells = [[Piece.parse(token) for token in row] for row in cells]
        self.rows = len(self._cells)
        self.cols = len(self._cells[0]) if self._cells else 0
        self.topology = topology if topology is not None else RectangularTopology(self.rows, self.cols)

    def is_inside(self, row, col):
        return self.topology.contains(row, col)

    # TODO(design): get_cell/set_cell trust the caller to have already
    # checked is_inside - GameController does, before ever calling
    # get_cell with a click-derived cell, but GameEngine and RuleEngine
    # call get_cell/set_cell freely without re-checking, relying on
    # RuleEngine's shape rules and the controller's upstream validation
    # to guarantee in-bounds coordinates. A validated public accessor
    # (raising a domain-specific exception on out-of-range access) with a
    # separate fast/unchecked internal path would centralize boundary
    # enforcement instead of leaving it as an implicit, spread-out
    # contract (Design by Contract, Fail Fast) - topology.contains() (see
    # above) is already the natural place to ask "is this valid", so this
    # would mean get_cell/set_cell consulting self.topology before
    # indexing rather than a separate check. Not added now: no
    # out-of-range access has ever actually occurred here, since every
    # caller today is already constrained upstream (click mapping,
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

    # TODO(design): Storage (_cells: a 2D list) and topology (which
    # positions exist, see board_topology.py) are two different concerns
    # that happen to agree today only because a rectangle is dense - a
    # 2D list has exactly one entry per (row, col) in range, same as
    # RectangularTopology says exists. An irregular board (holes, uneven
    # rows) or a hex/graph board breaks that agreement: a dense 2D list
    # would either waste cells that can never be reached or make "holes"
    # representable as valid-looking None entries indistinguishable from
    # an empty reachable square. A future BoardStorage abstraction
    # (get(position)/set(position, value)/positions()), with
    # MatrixBoardStorage as today's implementation and
    # SparseBoardStorage/DictionaryBoardStorage for irregular or graph
    # boards, would let storage vary independently of topology. Not
    # implemented now: today's rectangular _cells has no actual seam that
    # makes this a small change (unlike the topology injection above),
    # so it stays a documented required direction rather than a
    # premature abstraction guessed at without a second implementation.
    #
    # TODO(design): Each position also currently holds exactly one
    # Piece | None - a future variant with terrain, obstacles, traps,
    # cell-level effects, multiple occupants, or cell ownership would
    # need a richer Cell/CellState per position instead of a bare Piece.
    # This changes the central domain model (every get_cell/set_cell
    # caller assumes "a piece or nothing"), so it should stay deferred
    # until a concrete requirement actually needs one of those, not
    # introduced speculatively.

    # TODO(design): Board has no way to copy or snapshot its current
    # state. A Memento-style immutable snapshot (or a cheap copy-on-write
    # clone) would enable undo, move replay, AI search (trying a move and
    # rolling it back), or speculative "what if" analysis without
    # mutating the live game. Not needed for this iteration: the current
    # game has no undo/replay/AI requirement, so this would be
    # speculative infrastructure with no consumer yet.
