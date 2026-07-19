class CaptureKingWinCondition:
    """The current (and only) WinCondition: the game ends the instant a
    King is captured, and the capturing piece's color wins (Rule 11).

    Injected into GameEngine (Strategy Pattern) so "what ends the game"
    is a swappable policy rather than an if-statement inside motion
    resolution - a future variant with multiple kings, a score
    threshold, a target cell, territory control, survival time, or no
    king at all can supply its own WinCondition without touching
    GameEngine itself (Open/Closed Principle).

    check() is called once per resolved arrival (never for a friendly-
    collision stop or an airborne kill, since those aren't a completed
    move), strictly to *decide* whether the game just ended - by the
    time it runs, GameEngine has already applied the arrival to the
    board (Single Responsibility: this class never mutates state, only
    answers a question).
    """

    def check(self, moving_piece, captured_piece, board):
        """Returns the winning color ("w"/"b") if this arrival just
        ended the game, or None if it didn't. captured_piece is whatever
        piece previously occupied the destination (None if the square
        was empty)."""
        if captured_piece is not None and captured_piece.is_king():
            return moving_piece.color
        return None
