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


class GameOverEvent:
    """Published the instant a resolved arrival's injected WinCondition
    (see rules/win_condition.py) declares a winner - i.e. exactly when
    GameEngine.game_over transitions from False to True. Carries only
    domain values (no game_id/user_id - those are an application-layer
    concern, added by whatever translates this into a network message),
    same design as MoveResolvedEvent.

    reason defaults to "king_capture" - today's only real WinCondition -
    and is overridden explicitly by GameEngine.force_win's "forfeit"
    (Master Plan v2 Section 10.3/Decision 7). Not generalized further
    (e.g. into a reason enum/registry) until a second real reason beyond
    these two actually exists."""

    def __init__(self, winner, timestamp_ms=0, reason="king_capture"):
        self.winner = winner
        self.timestamp_ms = timestamp_ms
        self.reason = reason


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
