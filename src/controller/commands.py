class ClickCommand:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def execute(self, game):
        game.click(self.x, self.y)


class WaitCommand:
    def __init__(self, ms):
        self.ms = ms

    def execute(self, game):
        game.wait(self.ms)


class JumpCommand:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def execute(self, game):
        game.jump(self.x, self.y)


class PrintBoardCommand:
    def execute(self, game):
        game.print_board()


def parse_command(line):
    """Parses one command line into a Command, or None if unrecognized."""
    parts = line.split()

    if not parts:
        return None

    if parts[0] == "click":
        return ClickCommand(int(parts[1]), int(parts[2]))

    if parts[0] == "wait":
        return WaitCommand(int(parts[1]))

    if parts[0] == "jump":
        return JumpCommand(int(parts[1]), int(parts[2]))

    if line == "print board":
        return PrintBoardCommand()

    return None
