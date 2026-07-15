from kungfu_chess.engine.events import MoveResolvedEvent
from kungfu_chess.gui.observers import MovesLogObserver, ScoreObserver, algebraic


class FakePiece:
    def __init__(self, color, kind):
        self.color = color
        self.kind = kind

    def __str__(self):
        return f"{self.color}{self.kind}"


class TestAlgebraic:
    def test_bottom_left_is_a1(self):
        assert algebraic(row=7, col=0, board_rows=8) == "a1"

    def test_top_left_is_a8(self):
        assert algebraic(row=0, col=0, board_rows=8) == "a8"

    def test_e2(self):
        assert algebraic(row=6, col=4, board_rows=8) == "e2"

    def test_e4(self):
        assert algebraic(row=4, col=4, board_rows=8) == "e4"


class TestMovesLogObserver:
    def test_white_move_recorded_in_white_list(self):
        observer = MovesLogObserver(board_rows=8)
        event = MoveResolvedEvent(6, 4, 4, 4, moving_piece=FakePiece("w", "P"), timestamp_ms=0)
        observer(event)
        assert observer.white_moves == ["Pawn e2->e4 (0.0s)"]
        assert observer.black_moves == []

    def test_black_move_recorded_in_black_list(self):
        observer = MovesLogObserver(board_rows=8)
        event = MoveResolvedEvent(1, 4, 3, 4, moving_piece=FakePiece("b", "P"), timestamp_ms=0)
        observer(event)
        assert observer.black_moves == ["Pawn e7->e5 (0.0s)"]
        assert observer.white_moves == []

    def test_moves_accumulate_in_order(self):
        observer = MovesLogObserver(board_rows=8)
        observer(MoveResolvedEvent(6, 4, 4, 4, moving_piece=FakePiece("w", "P"), timestamp_ms=0))
        observer(MoveResolvedEvent(6, 3, 4, 3, moving_piece=FakePiece("w", "P"), timestamp_ms=0))
        assert observer.white_moves == ["Pawn e2->e4 (0.0s)", "Pawn d2->d4 (0.0s)"]

    def test_timestamp_is_formatted_as_seconds_with_one_decimal(self):
        observer = MovesLogObserver(board_rows=8)
        event = MoveResolvedEvent(6, 4, 4, 4, moving_piece=FakePiece("w", "P"), timestamp_ms=4300)
        observer(event)
        assert observer.white_moves == ["Pawn e2->e4 (4.3s)"]

    def test_every_piece_kind_gets_a_full_name(self):
        observer = MovesLogObserver(board_rows=8)
        expected = {
            "P": "Pawn", "N": "Knight", "B": "Bishop",
            "R": "Rook", "Q": "Queen", "K": "King",
        }
        for kind, name in expected.items():
            observer(MoveResolvedEvent(0, 0, 0, 1, moving_piece=FakePiece("w", kind), timestamp_ms=0))
        assert observer.white_moves == [f"{name} a8->b8 (0.0s)" for name in expected.values()]


class TestScoreObserver:
    def test_no_capture_does_not_change_score(self):
        observer = ScoreObserver()
        observer(MoveResolvedEvent(0, 0, 0, 1, moving_piece=FakePiece("w", "R"), captured_piece=None))
        assert observer.white_score == 0
        assert observer.black_score == 0

    def test_white_capturing_a_pawn_scores_one_for_white(self):
        observer = ScoreObserver()
        observer(MoveResolvedEvent(0, 0, 0, 1, moving_piece=FakePiece("w", "R"),
                                    captured_piece=FakePiece("b", "P")))
        assert observer.white_score == 1
        assert observer.black_score == 0

    def test_black_capturing_a_queen_scores_nine_for_black(self):
        observer = ScoreObserver()
        observer(MoveResolvedEvent(0, 0, 0, 1, moving_piece=FakePiece("b", "N"),
                                    captured_piece=FakePiece("w", "Q")))
        assert observer.black_score == 9
        assert observer.white_score == 0

    def test_scores_accumulate_across_captures(self):
        observer = ScoreObserver()
        observer(MoveResolvedEvent(0, 0, 0, 1, moving_piece=FakePiece("w", "R"),
                                    captured_piece=FakePiece("b", "P")))
        observer(MoveResolvedEvent(1, 1, 1, 2, moving_piece=FakePiece("w", "N"),
                                    captured_piece=FakePiece("b", "B")))
        assert observer.white_score == 1 + 3
