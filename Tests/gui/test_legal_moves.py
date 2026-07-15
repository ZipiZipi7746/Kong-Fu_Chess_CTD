from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.gui.legal_moves import legal_destinations


def make_board(rows):
    return Board(rows)


class FakeRuleEngine:
    """Only cells in `legal` are considered legal destinations - lets
    tests assert exactly what legal_destinations does with the answers
    it's given, without depending on real chess rules."""

    def __init__(self, legal):
        self.legal = set(legal)
        self.calls = []

    def is_legal(self, piece, from_row, from_col, to_row, to_col, board):
        self.calls.append((from_row, from_col, to_row, to_col))
        return (to_row, to_col) in self.legal


class TestLegalDestinations:
    def test_returns_only_cells_the_rule_engine_approves(self):
        board = make_board([["wR", ".", "."], [".", ".", "."]])
        rule_engine = FakeRuleEngine(legal=[(0, 1), (1, 0)])
        piece = Piece("w", "R")

        result = legal_destinations(piece, 0, 0, board, rule_engine)

        assert sorted(result) == [(0, 1), (1, 0)]

    def test_no_legal_destinations_returns_empty_list(self):
        board = make_board([["wR", "."]])
        rule_engine = FakeRuleEngine(legal=[])
        piece = Piece("w", "R")

        assert legal_destinations(piece, 0, 0, board, rule_engine) == []

    def test_checks_every_cell_on_the_board_exactly_once(self):
        board = make_board([["wR", "."], [".", "."]])
        rule_engine = FakeRuleEngine(legal=[])
        piece = Piece("w", "R")

        legal_destinations(piece, 0, 0, board, rule_engine)

        assert sorted(rule_engine.calls) == [
            (0, 0, 0, 0), (0, 0, 0, 1), (0, 0, 1, 0), (0, 0, 1, 1),
        ]

    def test_works_with_the_real_rule_engine(self):
        from kungfu_chess.rules.rule_engine import RuleEngine

        board = make_board([["wR", ".", "."]])
        piece = Piece("w", "R")

        result = legal_destinations(piece, 0, 0, board, RuleEngine())

        assert sorted(result) == [(0, 1), (0, 2)]
