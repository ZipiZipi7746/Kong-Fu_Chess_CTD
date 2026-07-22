"""Application-level events: server-wide, cross-cutting, and distinct from
both engine/events.py's domain events (scoped to one GameEngine/EventBus,
no game_id/user_id) and server/schemas.py's network JSON messages (no
Python objects). Published/consumed only through ApplicationMessageBus.

This is the Phase A subset only - GameService's own lifecycle moments
(GameStartedEvent) plus its translations of GameEngine's domain events
(GameMoveAppliedEvent/MoveRejectedEvent from MoveResolvedEvent-shaped
outcomes, GameEndedEvent from GameOverEvent). Room/matchmaking/connection
events (PlayerJoinedRoomEvent, MatchFoundEvent, PlayerDisconnectedEvent,
AutoResignAppliedEvent, RatingUpdatedEvent) belong to their own later
phases and are added following this same pattern when those phases start,
not built ahead of a consumer that needs them.
"""


class GameStartedEvent:
    """Published by GameService itself at session-creation time - see
    game_engine.py's docstring note: GameEngine has no "not started yet"
    state, so this is not a translation of any domain event."""

    def __init__(self, game_id, white, black, timestamp_ms=0):
        self.game_id = game_id
        self.white = white
        self.black = black
        self.timestamp_ms = timestamp_ms


class GameMoveAppliedEvent:
    """GameService's translation of a domain MoveResolvedEvent, with
    game_id attached."""

    def __init__(self, game_id, from_row, from_col, to_row, to_col,
                 moving_piece, captured_piece=None, timestamp_ms=0):
        self.game_id = game_id
        self.from_row = from_row
        self.from_col = from_col
        self.to_row = to_row
        self.to_col = to_col
        self.moving_piece = moving_piece
        self.captured_piece = captured_piece
        self.timestamp_ms = timestamp_ms


class MoveRejectedEvent:
    """Published by GameService itself (not a domain-event translation -
    GameEngine.request_move's rejection is a return value, not an event)
    when a move/jump command is rejected, so the gateway can notify only
    the requesting connection."""

    def __init__(self, game_id, user_id, reason, timestamp_ms=0):
        self.game_id = game_id
        self.user_id = user_id
        self.reason = reason
        self.timestamp_ms = timestamp_ms


class GameEndedEvent:
    """GameService's translation of a domain GameOverEvent, with game_id
    attached. reason passes through GameOverEvent.reason unchanged
    ("king_capture" or Decision 7's "forfeit")."""

    def __init__(self, game_id, winner, timestamp_ms=0, reason="king_capture"):
        self.game_id = game_id
        self.winner = winner
        self.timestamp_ms = timestamp_ms
        self.reason = reason
