class GameInputError(ValueError):
    """Base for expected, user-facing input failures (bad board text,
    eventually bad command text) - as opposed to an unrelated ValueError
    from a bug elsewhere in the call chain (e.g. a bad int() parse),
    which should propagate rather than being silently caught alongside
    these. Still a ValueError subclass, so any existing "except
    ValueError" keeps working unchanged; callers that want the narrower,
    precise contract can catch GameInputError instead (see main.py)."""


class BoardParsingError(GameInputError):
    """Base for board-text parsing failures (see BoardParser/BoardValidator)."""


class UnknownToken(BoardParsingError):
    pass


class RowWidthMismatch(BoardParsingError):
    pass
