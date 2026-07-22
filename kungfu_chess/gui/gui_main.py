"""Entrypoint: python -m kungfu_chess.gui.gui_main"""
from kungfu_chess.gui.game_loop import run  # pragma: no cover
from kungfu_chess.model.starting_position import standard_starting_board  # pragma: no cover


def main():  # pragma: no cover
    run(standard_starting_board())


if __name__ == "__main__":  # pragma: no cover
    main()
