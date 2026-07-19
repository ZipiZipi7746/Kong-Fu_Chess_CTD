import itertools

from kungfu_chess.io.board_parser import BoardParser
from kungfu_chess.engine.events import GameOverEvent, MoveResolvedEvent
from kungfu_chess.messaging.application_events import (
    GameStartedEvent,
    GameMoveAppliedEvent,
    MoveRejectedEvent,
    GameEndedEvent,
)
from kungfu_chess.application.game_session import GameSession

# Maps GameEngine.request_move's own result vocabulary ("game_over",
# "invalid", "blocked", "scheduled") to the wire-facing reason codes named
# in the architecture plan's protocol table (Part 6) - kept as a small,
# explicit table rather than a mechanical .upper() so the two vocabularies
# can diverge on purpose (e.g. "invalid" -> "INVALID_MOVE", not "INVALID").
_MOVE_REJECTION_REASONS = {
    "invalid": "INVALID_MOVE",
    "blocked": "BLOCKED",
    "game_over": "GAME_OVER",
}

_STANDARD_STARTING_BOARD_LINES = [
    "Board:",
    "bR bN bB bQ bK bB bN bR",
    "bP bP bP bP bP bP bP bP",
    ". . . . . . . .",
    ". . . . . . . .",
    ". . . . . . . .",
    ". . . . . . . .",
    "wP wP wP wP wP wP wP wP",
    "wR wN wB wQ wK wB wN wR",
    "Commands:",
]


def _standard_starting_board():
    board, _commands = BoardParser().parse(_STANDARD_STARTING_BOARD_LINES)
    return board


class GameService:
    """The single place a network move/jump command becomes a call into
    GameEngine (Part 8 of the architecture plan) - the server's
    equivalent of GameController, calling GameEngine directly rather than
    GameController.click/jump (see the plan's verified reason: click()
    is a pixel/single-selection abstraction with no place for two
    independent remote players).

    Owns the GameSession registry itself (Phase A has no GameRepository
    yet); publishes to the injected ApplicationMessageBus and subscribes
    to each session's own per-game EventBus to translate domain events
    (MoveResolvedEvent/GameOverEvent) into application events
    (GameMoveAppliedEvent/GameEndedEvent). GameStartedEvent has no domain
    event to translate - GameEngine has no "not started" state - so it is
    published directly by create_session() at session-creation time.
    """

    def __init__(self, message_bus):
        self._message_bus = message_bus
        self._sessions = {}
        self._game_id_counter = itertools.count(1)

    def create_session(self, white, black, board=None, jump_duration_ms=1000,
                        move_cooldown_ms=None, jump_cooldown_ms=None):
        game_id = f"g_{next(self._game_id_counter)}"
        session = GameSession(
            game_id=game_id,
            board=board if board is not None else _standard_starting_board(),
            white=white, black=black, jump_duration_ms=jump_duration_ms,
            move_cooldown_ms=move_cooldown_ms, jump_cooldown_ms=jump_cooldown_ms)
        session.event_bus.subscribe(self._make_domain_event_translator(session))
        self._sessions[game_id] = session

        self._message_bus.publish(GameStartedEvent(
            game_id=game_id, white=white, black=black))

        return session

    def get_session(self, game_id):
        return self._sessions.get(game_id)

    def sessions(self):
        """A snapshot copy of the session registry, keyed by game_id -
        used by server_main.py's periodic tick loop to decide which
        sessions still need advance_time (Part 10's hybrid design). A
        copy, not the live dict, so the loop can safely iterate it while
        create_session runs concurrently elsewhere."""
        return dict(self._sessions)

    def _make_domain_event_translator(self, session):
        def translate(event):
            if isinstance(event, MoveResolvedEvent):
                self._message_bus.publish(GameMoveAppliedEvent(
                    game_id=session.game_id,
                    from_row=event.from_row, from_col=event.from_col,
                    to_row=event.to_row, to_col=event.to_col,
                    moving_piece=event.moving_piece, captured_piece=event.captured_piece,
                    timestamp_ms=event.timestamp_ms))
            elif isinstance(event, GameOverEvent):
                self._message_bus.publish(GameEndedEvent(
                    game_id=session.game_id, winner=event.winner,
                    timestamp_ms=event.timestamp_ms))
        return translate

    async def handle_move_request(self, game_id, requester, from_row, from_col, to_row, to_col):
        session = self._sessions.get(game_id)
        if session is None:
            return "game_not_found"

        async with session.lock:
            piece = session.engine.board.get_cell(from_row, from_col)
            # Authorization is "does the requester own this piece's
            # color", never "whose turn is it" - see GameSession's
            # docstring: this engine has no turn concept, and both
            # colors legitimately have motions in flight at once.
            if piece is None or session.color_for(requester) != piece.color:
                self._message_bus.publish(MoveRejectedEvent(
                    game_id=game_id, user_id=requester, reason="NOT_YOUR_TURN_OR_ACTION"))
                return "rejected"

            result = session.engine.request_move(from_row, from_col, to_row, to_col)
            if result != "scheduled":
                reason = _MOVE_REJECTION_REASONS.get(result, result.upper())
                self._message_bus.publish(MoveRejectedEvent(
                    game_id=game_id, user_id=requester, reason=reason))
                return "rejected"
            return "scheduled"

    async def handle_jump_request(self, game_id, requester, row, col):
        session = self._sessions.get(game_id)
        if session is None:
            return False

        async with session.lock:
            piece = session.engine.board.get_cell(row, col)
            if piece is None or session.color_for(requester) != piece.color:
                self._message_bus.publish(MoveRejectedEvent(
                    game_id=game_id, user_id=requester, reason="NOT_YOUR_TURN_OR_ACTION"))
                return False

            return session.engine.request_jump(row, col)

    async def tick(self, game_id, elapsed_ms):
        session = self._sessions.get(game_id)
        if session is None:
            return

        async with session.lock:
            session.engine.advance_time(elapsed_ms)
