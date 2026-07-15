"""Pure text layout: each function returns what to draw and where -
(text, x, y) tuples - never draws anything itself. Only ImgRenderer
actually calls put_text.

Single-color, not paired white/black - each side panel (left/right of
the board) shows exactly one player's name, score and moves log, so
the caller invokes these once per panel with that panel's own x/y."""


def render_score(score, x, y):
    return [(f"Score: {score}", x, y)]


def render_player_name(name, x, y):
    return [(name, x, y)]


def render_moves_log(moves, x, y, line_height=20, max_lines=10):
    recent = moves[-max_lines:]
    return [(text, x, y + i * line_height) for i, text in enumerate(recent)]


_COLOR_NAMES = {"w": "White", "b": "Black"}


def render_game_over(winner_color, x, y):
    return [(f"{_COLOR_NAMES[winner_color]} Wins!", x, y)]
