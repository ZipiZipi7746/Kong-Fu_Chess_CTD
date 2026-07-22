"""Centralized GUI asset paths - the single place "where the board
image/piece sprites live" is defined. gui/game_loop.py and
gui/network/network_game_loop.py both default to these instead of each
hardcoding the same path strings independently."""

DEFAULT_BOARD_IMAGE_PATH = "assets/board.png"
DEFAULT_PIECES_ROOT = "assets/pieces_mine"
