from kungfu_chess.gui.hud import render_moves_log, render_player_names, render_score


class TestRenderScore:
    def test_returns_two_lines_at_increasing_y(self):
        lines = render_score(white_score=3, black_score=5, x=10, y=20, line_height=25)
        assert lines == [("White: 3", 10, 20), ("Black: 5", 10, 45)]


class TestRenderPlayerNames:
    def test_returns_two_lines(self):
        lines = render_player_names("Alice", "Bob", x=10, y=20, line_height=25)
        assert lines == [("Alice", 10, 20), ("Bob", 10, 45)]


class TestRenderMovesLog:
    def test_pairs_white_and_black_moves_on_the_same_line(self):
        lines = render_moves_log(["e2->e4"], ["e7->e5"], x=10, y=100, line_height=20)
        assert lines == [("e2->e4  e7->e5", 10, 100)]

    def test_handles_uneven_move_counts(self):
        lines = render_moves_log(["e2->e4", "d2->d4"], ["e7->e5"], x=10, y=100, line_height=20)
        assert lines == [("e2->e4  e7->e5", 10, 100), ("d2->d4  ", 10, 120)]

    def test_only_shows_the_most_recent_max_lines(self):
        white = [f"move{i}" for i in range(20)]
        black = [f"move{i}" for i in range(20)]
        lines = render_moves_log(white, black, x=0, y=0, line_height=10, max_lines=3)
        assert len(lines) == 3
        assert lines[0][0] == "move17  move17"
        assert lines[2][0] == "move19  move19"

    def test_empty_logs_produce_no_lines(self):
        assert render_moves_log([], [], x=0, y=0, line_height=10) == []
