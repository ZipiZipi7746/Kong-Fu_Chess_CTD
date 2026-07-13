from src.domain.board import Board
from src.io.board_validator import BoardValidator


class BoardParser:

    def parse(self, lines=None):
        """lines is an optional Dependency Injection point: pass an
        iterable of strings to parse directly (used by tests, avoiding
        any need to monkeypatch input()/stdin). In production, main.py
        calls parse() with no arguments and it reads from stdin exactly
        as before."""
        board_rows = []
        commands = []

        if lines is None:
            lines = self._read_stdin()  # pragma: no cover (see note below)

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

    @staticmethod
    def _read_stdin():  # pragma: no cover
        # This is the single, deliberately tiny I/O boundary that talks
        # to real stdin. It is excluded from coverage rather than tested
        # via monkeypatching input()/sys.stdin, per the "no monkeypatching"
        # requirement. It is exercised by a real subprocess+piped-stdin
        # test instead (test_board_parser.py::TestReadStdinSubprocess),
        # which runs the unmodified code against real input with no
        # patching at all - it just can't contribute to in-process
        # coverage numbers since it executes in a separate process.
        lines = []
        while True:
            try:
                lines.append(input())
            except EOFError:
                break
        return lines
