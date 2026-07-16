from kungfu_chess.gui.hud.hud import render_game_over, render_moves_log, render_player_name, render_score


class TestRenderScore:
    def test_returns_one_line(self):
        lines = render_score(score=3, x=10, y=20)
        assert lines == [("Score: 3", 10, 20)]


class TestRenderPlayerName:
    def test_returns_one_line(self):
        lines = render_player_name("Alice", x=10, y=20)
        assert lines == [("Alice", 10, 20)]


class TestRenderMovesLog:
    def test_returns_one_line_per_move_at_increasing_y(self):
        lines = render_moves_log(["e2->e4", "e7->e5"], x=10, y=100, line_height=20)
        assert lines == [("e2->e4", 10, 100), ("e7->e5", 10, 120)]

    def test_only_shows_the_most_recent_max_lines(self):
        moves = [f"move{i}" for i in range(20)]
        lines = render_moves_log(moves, x=0, y=0, line_height=10, max_lines=3)
        assert len(lines) == 3
        assert lines[0][0] == "move17"
        assert lines[2][0] == "move19"

    def test_empty_log_produces_no_lines(self):
        assert render_moves_log([], x=0, y=0, line_height=10) == []


class TestRenderGameOver:
    def test_white_winner_produces_white_wins_message(self):
        assert render_game_over("w", x=10, y=20) == [("White Wins!", 10, 20)]

    def test_black_winner_produces_black_wins_message(self):
        assert render_game_over("b", x=10, y=20) == [("Black Wins!", 10, 20)]
