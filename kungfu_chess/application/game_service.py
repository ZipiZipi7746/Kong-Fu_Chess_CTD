import itertools

from kungfu_chess.engine.events import GameOverEvent, MoveResolvedEvent
from kungfu_chess.messaging.application_events import (
    GameStartedEvent,
    GameMoveAppliedEvent,
    MoveRejectedEvent,
    GameEndedEvent,
)
from kungfu_chess.application import rating_service
from kungfu_chess.application.game_session import GameSession
from kungfu_chess.model.starting_position import standard_starting_board
from kungfu_chess.persistence.in_memory_repositories import InMemoryUserRepository

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

    def __init__(self, message_bus, user_repository=None):
        self._message_bus = message_bus
        self._sessions = {}
        self._game_id_counter = itertools.count(1)
        # Only ever consulted for rated games (Decision 14) - quick_local
        # games (rated=False, the default) never touch this. Defaults to
        # a fresh, empty repository so GameService remains constructible
        # standalone (matching this project's param=None DI convention),
        # though a real deployment shares the same UserRepository
        # instance AuthenticationService uses (see server_main.py).
        self._user_repository = user_repository if user_repository is not None else InMemoryUserRepository()

    def create_session(self, white, black, board=None, jump_duration_ms=1000,
                        move_cooldown_ms=None, jump_cooldown_ms=None, rated=False):
        game_id = f"g_{next(self._game_id_counter)}"
        session = GameSession(
            game_id=game_id,
            board=board if board is not None else standard_starting_board(),
            white=white, black=black, jump_duration_ms=jump_duration_ms,
            move_cooldown_ms=move_cooldown_ms, jump_cooldown_ms=jump_cooldown_ms,
            rated=rated)
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
                if session.rated and not session.rating_applied:
                    session.rating_applied = True
                    self._apply_rating(session, event.winner)
                self._message_bus.publish(GameEndedEvent(
                    game_id=session.game_id, winner=event.winner,
                    timestamp_ms=event.timestamp_ms, reason=event.reason))
        return translate

    def _apply_rating(self, session, winner):
        white_user = self._user_repository.get_by_username(session.white)
        black_user = self._user_repository.get_by_username(session.black)
        if white_user is None or black_user is None:
            return  # not real accounts (e.g. a rated session in a test) - nothing to update

        new_white, new_black = rating_service.apply_game_result(
            white_user.rating, black_user.rating, winner)
        self._user_repository.update_rating(white_user.user_id, new_white)
        self._user_repository.update_rating(black_user.user_id, new_black)

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

    async def forfeit(self, game_id, forfeiting_identity):
        """Master Plan v2 Section 10.3/Decision 7: called once a
        disconnected player's grace period has elapsed with no
        reconnect. Ends the game via GameEngine.force_win - the same
        GameOverEvent -> GameEndedEvent path (and rating application,
        for a rated game) as any other win, just for the opponent of
        whoever failed to return in time."""
        session = self._sessions.get(game_id)
        if session is None:
            return

        async with session.lock:
            color = session.color_for(forfeiting_identity)
            if color is None:
                return
            winner = "b" if color == "w" else "w"
            session.engine.force_win(winner)
