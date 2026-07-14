"""Entrypoint: python -m kungfu_chess.gui.gui_main"""
from kungfu_chess.gui.game_loop import run  # pragma: no cover
from kungfu_chess.model.board import Board  # pragma: no cover


def main():  # pragma: no cover
    rows = [
        ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
        ["bP"] * 8,
        ["."] * 8, ["."] * 8, ["."] * 8, ["."] * 8,
        ["wP"] * 8,
        ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"],
    ]
    run(Board(rows))


if __name__ == "__main__":  # pragma: no cover
    main()
