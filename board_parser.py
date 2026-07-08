from board import Board
from board_validator import BoardValidator


class BoardParser:

    def parse(self):
        board_rows = []
        commands = []

        lines = []

        while True:
            try:
                lines.append(input())
            except EOFError:
                break

        mode = None

        for line in lines:
            line = line.strip()
            if line == "Board:":
                mode = "board"
                continue

            if line == "Commands:":
                mode = "commands"
                continue

            if mode == "board":
                board_rows.append(line.split())

            elif mode == "commands":
                commands.append(line)

        BoardValidator.validate(board_rows)

        return Board(board_rows), commands