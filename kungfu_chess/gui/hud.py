"""Pure text layout: each function returns what to draw and where -
(text, x, y) tuples - never draws anything itself. Only ImgRenderer
actually calls put_text."""


def render_score(white_score, black_score, x, y, line_height=28):
    return [
        (f"White: {white_score}", x, y),
        (f"Black: {black_score}", x, y + line_height),
    ]


def render_player_names(white_name, black_name, x, y, line_height=28):
    return [
        (white_name, x, y),
        (black_name, x, y + line_height),
    ]


def render_moves_log(white_moves, black_moves, x, y, line_height=20, max_lines=10):
    recent_white = white_moves[-max_lines:]
    recent_black = black_moves[-max_lines:]
    line_count = max(len(recent_white), len(recent_black))

    lines = []
    for i in range(line_count):
        white_text = recent_white[i] if i < len(recent_white) else ""
        black_text = recent_black[i] if i < len(recent_black) else ""
        lines.append((f"{white_text}  {black_text}", x, y + i * line_height))
    return lines
