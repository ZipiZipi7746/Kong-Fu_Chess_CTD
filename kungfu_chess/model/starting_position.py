"""The standard chess starting position - the single source every
entrypoint that needs a fresh board builds from (application/
game_service.py's default GameSession board, gui/gui_main.py's local
single-player game), instead of each independently encoding the same
8x8 layout."""

from kungfu_chess.model.board import Board

STANDARD_STARTING_ROWS = [
    ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
    ["bP"] * 8,
    ["."] * 8, ["."] * 8, ["."] * 8, ["."] * 8,
    ["wP"] * 8,
    ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"],
]


def standard_starting_board():
    return Board(STANDARD_STARTING_ROWS)
