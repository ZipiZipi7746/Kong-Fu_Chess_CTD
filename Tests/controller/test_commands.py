from src.controller.commands import (
    ClickCommand,
    WaitCommand,
    JumpCommand,
    PrintBoardCommand,
    parse_command,
)


class FakeGame:
    """Test double injected into Command.execute() - avoids needing a
    real GameController/board for these purely-dispatching classes."""

    def __init__(self):
        self.clicks = []
        self.waits = []
        self.jumps = []
        self.printed = False

    def click(self, x, y):
        self.clicks.append((x, y))

    def wait(self, ms):
        self.waits.append(ms)

    def jump(self, x, y):
        self.jumps.append((x, y))

    def print_board(self):
        self.printed = True


class TestClickCommand:
    def test_execute_calls_click_with_coordinates(self):
        game = FakeGame()
        ClickCommand(10, 20).execute(game)
        assert game.clicks == [(10, 20)]


class TestWaitCommand:
    def test_execute_calls_wait_with_ms(self):
        game = FakeGame()
        WaitCommand(500).execute(game)
        assert game.waits == [500]


class TestJumpCommand:
    def test_execute_calls_jump_with_coordinates(self):
        game = FakeGame()
        JumpCommand(30, 40).execute(game)
        assert game.jumps == [(30, 40)]


class TestPrintBoardCommand:
    def test_execute_calls_print_board(self):
        game = FakeGame()
        PrintBoardCommand().execute(game)
        assert game.printed is True


class TestParseCommand:
    def test_empty_line_returns_none(self):
        assert parse_command("") is None

    def test_whitespace_only_line_returns_none(self):
        assert parse_command("   ") is None

    def test_parses_click(self):
        command = parse_command("click 100 200")
        assert isinstance(command, ClickCommand)
        assert (command.x, command.y) == (100, 200)

    def test_parses_wait(self):
        command = parse_command("wait 1000")
        assert isinstance(command, WaitCommand)
        assert command.ms == 1000

    def test_parses_jump(self):
        command = parse_command("jump 5 6")
        assert isinstance(command, JumpCommand)
        assert (command.x, command.y) == (5, 6)

    def test_parses_print_board(self):
        command = parse_command("print board")
        assert isinstance(command, PrintBoardCommand)

    def test_unrecognized_command_returns_none(self):
        assert parse_command("dance 1 2") is None
