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

    # TODO(design): subscribe() accepts anything callable - a plain
    # function or a class with __call__, per the current subscribers
    # (MovesLogObserver, ScoreObserver). That's appropriate for this
    # small, fixed set of listeners. If the number/variety of subscriber
    # types grows, an explicit listener Protocol/interface (e.g.
    # requiring an on_move_resolved(event) method rather than "any
    # callable") would make the contract discoverable and statically
    # checkable (Observer Pattern, Publish-Subscribe, Dependency
    # Inversion against an explicit port). Not introduced now: "anything
    # callable" is simple, already testable with a plain list.append, and
    # a typed protocol would be overengineering for two subscribers.
    def __init__(self):
        self._subscribers = []

    def subscribe(self, callback):
        self._subscribers.append(callback)

    def publish(self, event):
        for callback in self._subscribers:
            callback(event)
