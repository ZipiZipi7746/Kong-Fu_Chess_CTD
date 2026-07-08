from board_parser import BoardParser
from commands import parse_command
from game import Game


def main():
    parser = BoardParser()

    try:
        board, command_lines = parser.parse()
        game = Game(board)

        for line in command_lines:
            command = parse_command(line)
            if command is not None:
                command.execute(game)

    except ValueError as e:
        print(f"ERROR {e}")


if __name__ == "__main__":
    main()
