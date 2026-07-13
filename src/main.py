from src.io.board_parser import BoardParser
from src.controller.commands import parse_command
from src.controller.game_controller import GameController


def run(lines=None):
    """Testable entry point: lines is an optional DI point (a list of
    input strings) so tests can drive the whole pipeline without
    monkeypatching stdin. main() calls this with no arguments, which
    reads from stdin exactly as before."""
    parser = BoardParser()

    try:
        board, command_lines = parser.parse(lines)
        controller = GameController(board)

        for line in command_lines:
            command = parse_command(line)
            if command is not None:
                command.execute(controller)

    except ValueError as e:
        print(f"ERROR {e}")


def main():  # pragma: no cover
    # Thin CLI wrapper around run() that reads real stdin - exercised by
    # the real subprocess test in test_main.py, not monkeypatching.
    run()


if __name__ == "__main__":
    main()
