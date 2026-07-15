class MoveResolvedEvent:
    """Published when a motion successfully completes its journey (Rule
    10's atomic arrival) - not for a friendly-collision stop or an
    enemy-airborne kill, since those aren't a completed move."""

    def __init__(self, from_row, from_col, to_row, to_col, moving_piece, captured_piece=None,
                 timestamp_ms=0):
        self.from_row = from_row
        self.from_col = from_col
        self.to_row = to_row
        self.to_col = to_col
        self.moving_piece = moving_piece
        self.captured_piece = captured_piece
        self.timestamp_ms = timestamp_ms


class EventBus:
    """Minimal Subject/Observer hub: GameEngine publishes, anything
    (a moves-log, a score tracker, a sound effect later) subscribes.
    GameEngine has zero knowledge of who's listening or why."""

    def __init__(self):
        self._subscribers = []

    def subscribe(self, callback):
        self._subscribers.append(callback)

    def publish(self, event):
        for callback in self._subscribers:
            callback(event)
