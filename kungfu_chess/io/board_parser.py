from kungfu_chess.model.board import Board
from kungfu_chess.io.board_validator import BoardValidator


class BoardParser:
    # TODO(design): This is the project's one existing example of the
    # boundary a future variant-loading mechanism would extend: text in,
    # a domain object out, validated before the engine ever sees it.
    # Declarative board *layout* (which cells exist, starting piece
    # placement) is a reasonable fit for simple configuration data (this
    # text DSL today; JSON/YAML would work the same way) - but piece
    # *behavior* is not: a genuinely new movement rule is executable
    # logic (a PieceRule/is_legal implementation), not data, and should
    # stay registered Python strategy code rather than pushed into a
    # config format. If runtime/plugin loading ever becomes a real
    # requirement, it belongs at this parsing boundary - constructing
    # and registering domain objects - never inside RuleEngine, GameEngine
    # or Board themselves (Plugin Architecture, Registry/Factory Pattern,
    # Dependency Injection). Not built now: nothing in this project loads
    # rules or layouts from outside the codebase yet.
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
