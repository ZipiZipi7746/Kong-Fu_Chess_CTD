"""Accepts WebSocket connections, reads/writes JSON frames, delegates
every command to GameService/AuthenticationService - zero rule logic of
its own. Never imports kungfu_chess.model, kungfu_chess.rules,
kungfu_chess.realtime, or kungfu_chess.persistence.sqlite directly (the
architecture plan's forbidden-imports rule, Master Plan v2 Section 5);
board state only ever reaches this module already serialized, via
application.dto, and accounts only ever reach it through
AuthenticationService.

Phase A/B's join_game "quick_local" mode remains available for local/
offline-style testing (the first connection to request it waits, the
second pairs with it - first = White, second = Black - unrated). Phase
C adds a separate "play" queue (Decisions 5/6/13): matched pairs are
always rated (Decision 14); quick_local is not replaced by it. Phase E
(rooms) will add a third join path without changing anything below.

Phase B replaces the password-less "connect" message with the permanent
CLI login flow (Decision 2): "register" creates an account, "login"
authenticates and returns a session token. Phase D consumes that token
fully: a mid-game disconnect starts a grace-period timer (Decision 7)
and notifies the opponent ("player_disconnected"); a "reconnect" message
carrying the token rebinds the new connection to the same GameSession
and sends one fresh state_snapshot (never an event replay - see
Section 3.1's board-sync guarantee) if the window hasn't elapsed.
GameSession.color_for/white/black are still plain display-name strings
(unchanged from Phase A) - only the identification step gained real
credentials.

Also guards against a duplicate move_request retry (Section 3.3's
hardening note): an already-scheduled move's message_id is cached and
its response replayed rather than reprocessed, so a client resending
after a lost ack can never schedule the same Motion twice.

Phase E adds "create_room"/"join_room": the creator is White, the
second joiner is Black (starting a rated GameSession exactly like
"play" does), and everyone after that is a read-only spectator -
RoomService enforces the spectator cap and room-membership rules;
this module only translates that into wire messages and, for a
spectator, one catch-up state_snapshot (never an event replay, same
guarantee as a fresh join or a reconnect). _broadcast/connections_in_game
already generalize to "everyone in this game, players and spectators
alike" - a spectator connection is just another entry returned by
connections_in_game, not a special case. A spectator's move_request is
already rejected with no new authorization code: GameSession.color_for
returns None for anyone who isn't white/black, and
GameService.handle_move_request already rejects a None color.

Every wire message type name is imported from server.protocol rather
than re-typed here as a string literal, so this module and every client
can never silently drift on the spelling of a message type.
"""

import asyncio
import logging
import uuid

from kungfu_chess.application import dto
from kungfu_chess.application.auth_service import AuthenticationService, InvalidCredentialsError
from kungfu_chess.application.connection_service import ConnectionService
from kungfu_chess.application.matchmaking_service import MatchmakingService
from kungfu_chess.application.room_service import (
    RoomNotFoundError,
    RoomService,
    SpectatorCapExceededError,
)
from kungfu_chess.messaging.application_events import (
    GameStartedEvent,
    GameMoveAppliedEvent,
    MoveRejectedEvent,
    GameEndedEvent,
)
from kungfu_chess.persistence.repositories import DuplicateUsernameError
from kungfu_chess.server import protocol, schemas
from kungfu_chess.server.connection_manager import ConnectionManager
from kungfu_chess.server.logging_config import hash_token

logger = logging.getLogger(__name__)


class WebSocketGateway:
    def __init__(self, game_service, message_bus, connection_manager=None,
                 auth_service=None, matchmaking_service=None, connection_service=None,
                 room_service=None):
        self._game_service = game_service
        self._message_bus = message_bus
        self._connections = connection_manager if connection_manager is not None else ConnectionManager()
        self._auth_service = auth_service if auth_service is not None else AuthenticationService()
        self._matchmaking_service = (
            matchmaking_service if matchmaking_service is not None else MatchmakingService())
        self._connection_service = (
            connection_service if connection_service is not None else ConnectionService())
        self._room_service = room_service if room_service is not None else RoomService()
        # room_id -> game_id, populated once a room's second joiner
        # starts the GameSession - bridges RoomService's own rooms
        # (which know nothing about GameService) and GameService's
        # sessions (which know nothing about rooms), so a later
        # spectator join_room can find the right session to catch up on.
        self._game_id_by_room_id = {}
        self._quick_local_waiting_connection_id = None
        # Two independent monotonic counters, each driven only by their
        # own advance_*_clock method (server_main.py's tick loop calls
        # both every tick) - never a real wall clock, same deterministic-
        # time convention as RealTimeArbiter (Rule 9). Kept separate
        # rather than merged into one shared counter: matchmaking and
        # connection tracking are unrelated concerns that only
        # coincidentally advance by the same tick_interval_ms each call.
        self._matchmaking_clock_ms = 0
        self._connection_clock_ms = 0
        # message_id -> cached response envelope, for exactly the
        # move_request dedup case above. Deliberately unbounded for now
        # (message_ids are UUIDs, one entry per accepted move) - a TTL/
        # eviction policy is a real future concern for a long-running
        # server, not addressed in this pass.
        self._processed_move_requests = {}

        message_bus.subscribe(GameStartedEvent, self._on_game_started)
        message_bus.subscribe(GameMoveAppliedEvent, self._on_game_move_applied)
        message_bus.subscribe(GameEndedEvent, self._on_game_ended)
        message_bus.subscribe(MoveRejectedEvent, self._on_move_rejected)

    async def handle_connection(self, websocket):
        connection_id = str(uuid.uuid4())
        self._connections.register(connection_id, websocket)
        try:
            async for raw in websocket:
                await self._dispatch(connection_id, websocket, raw)
        finally:
            if self._quick_local_waiting_connection_id == connection_id:
                self._quick_local_waiting_connection_id = None
            await self._handle_disconnect(connection_id)
            self._connections.unregister(connection_id)

    async def _handle_disconnect(self, connection_id):
        room_id = self._connections.get_room_id(connection_id)
        identity = self._connections.get_identity(connection_id)
        if room_id is not None and identity is not None:
            self._room_service.leave_room(room_id, identity)

        game_id = self._connections.get_game_id(connection_id)
        if game_id is None or identity is None:
            return

        session = self._game_service.get_session(game_id)
        if session is None or session.engine.game_over:
            return  # nothing to track - the game already ended

        self._connection_service.record_disconnect(game_id, identity, self._connection_clock_ms)

        # Every other connection in the game - players and spectators
        # alike (Phase E) - is notified, not just "the opponent".
        notice = schemas.make_envelope(
            protocol.PLAYER_DISCONNECTED,
            {"grace_period_ms": self._connection_service.grace_period_ms},
            game_id=game_id)
        for other_id in self._connections.connections_in_game(game_id):
            if other_id == connection_id:
                continue
            await self._send(self._connections.get_socket(other_id), notice)

    # ---------------------------------------------------------------
    # Incoming client -> server messages
    # ---------------------------------------------------------------

    _HANDLER_NAMES = {
        protocol.REGISTER: "_handle_register",
        protocol.LOGIN: "_handle_login",
        protocol.RECONNECT: "_handle_reconnect",
        protocol.JOIN_GAME: "_handle_join_game",
        protocol.PLAY: "_handle_play",
        protocol.CANCEL_MATCHMAKING: "_handle_cancel_matchmaking",
        protocol.CREATE_ROOM: "_handle_create_room",
        protocol.JOIN_ROOM: "_handle_join_room",
        protocol.MOVE_REQUEST: "_handle_move_request",
        protocol.JUMP_REQUEST: "_handle_jump_request",
        protocol.PING: "_handle_ping",
    }

    async def _dispatch(self, connection_id, websocket, raw):
        try:
            envelope = schemas.decode(raw)
        except schemas.MalformedMessageError as exc:
            await self._send(websocket, schemas.make_envelope(
                protocol.ERROR, {"code": "MALFORMED_MESSAGE", "message": str(exc)}))
            return

        handler_name = self._HANDLER_NAMES.get(envelope["type"])
        if handler_name is None:
            await self._send(websocket, schemas.make_envelope(
                protocol.ERROR, {"code": "UNKNOWN_MESSAGE_TYPE", "message": envelope["type"]},
                correlation_id=envelope["message_id"]))
            return

        logger.debug(
            "dispatching %s", envelope["type"],
            extra={"message_id": envelope["message_id"], "game_id": envelope["game_id"]})
        await getattr(self, handler_name)(connection_id, websocket, envelope)

    async def _handle_register(self, connection_id, websocket, envelope):
        payload = envelope["payload"]
        try:
            self._auth_service.register(payload["username"], payload["password"])
        except DuplicateUsernameError:
            await self._send(websocket, schemas.make_envelope(
                protocol.ERROR, {"code": "USERNAME_TAKEN", "message": payload["username"]},
                correlation_id=envelope["message_id"]))
            return
        await self._send(websocket, schemas.make_envelope(
            protocol.REGISTERED, {"username": payload["username"]},
            correlation_id=envelope["message_id"]))

    async def _handle_login(self, connection_id, websocket, envelope):
        payload = envelope["payload"]
        try:
            token = self._auth_service.login(payload["username"], payload["password"])
        except InvalidCredentialsError:
            await self._send(websocket, schemas.make_envelope(
                protocol.ERROR, {"code": "INVALID_CREDENTIALS"},
                correlation_id=envelope["message_id"]))
            return
        self._connections.set_identity(connection_id, payload["username"])
        self._connections.set_session_token(connection_id, token)
        logger.info(
            "login succeeded for %s", payload["username"],
            extra={"message_id": envelope["message_id"], "session_token_hash": hash_token(token)})
        await self._send(websocket, schemas.make_envelope(
            protocol.LOGIN_OK, {"username": payload["username"], "session_token": token},
            correlation_id=envelope["message_id"]))

    async def _handle_ping(self, connection_id, websocket, envelope):
        await self._send(websocket, schemas.make_envelope(
            protocol.PONG, {}, correlation_id=envelope["message_id"]))

    async def _handle_reconnect(self, connection_id, websocket, envelope):
        token = envelope["payload"].get("session_token")
        user = self._auth_service.resolve_token(token) if token else None
        logger.info(
            "reconnect attempt", extra={
                "message_id": envelope["message_id"], "session_token_hash": hash_token(token)})
        if user is None:
            await self._send(websocket, schemas.make_envelope(
                protocol.ERROR, {"code": "NO_RECONNECTABLE_GAME"},
                correlation_id=envelope["message_id"]))
            return

        game_id = self._connection_service.reconnect(user.username)
        session = self._game_service.get_session(game_id) if game_id is not None else None
        if session is None:
            await self._send(websocket, schemas.make_envelope(
                protocol.ERROR, {"code": "NO_RECONNECTABLE_GAME"},
                correlation_id=envelope["message_id"]))
            return

        self._connections.set_identity(connection_id, user.username)
        self._connections.set_session_token(connection_id, token)
        self._connections.set_game_id(connection_id, game_id)

        # One full state_snapshot on rebind, never an event replay - the
        # exact same guarantee _start_game already gives a fresh join
        # (Section 3.1).
        await self._send(websocket, schemas.make_envelope(
            protocol.STATE_SNAPSHOT, dto.build_state_snapshot(session), game_id=game_id))

    async def _handle_join_game(self, connection_id, websocket, envelope):
        if self._quick_local_waiting_connection_id is None:
            self._quick_local_waiting_connection_id = connection_id
            return

        white_id = self._quick_local_waiting_connection_id
        black_id = connection_id
        self._quick_local_waiting_connection_id = None

        await self._start_game(white_id, black_id, rated=False)

    async def _handle_play(self, connection_id, websocket, envelope):
        identity = self._connections.get_identity(connection_id)
        if identity is None:
            await self._send(websocket, schemas.make_envelope(
                protocol.ERROR, {"code": "NOT_LOGGED_IN"}, correlation_id=envelope["message_id"]))
            return
        if self._matchmaking_service.is_queued(identity):
            return  # already searching - a duplicate "play" is a no-op, not an error

        user = self._auth_service.get_user(identity)
        if user is None:
            return  # shouldn't happen - a successful login already implies a real account

        self._matchmaking_service.enqueue(identity, user.rating, now_ms=self._matchmaking_clock_ms)
        await self._send(websocket, schemas.make_envelope(
            protocol.SEARCHING_MATCH, {}, correlation_id=envelope["message_id"]))

    async def _handle_cancel_matchmaking(self, connection_id, websocket, envelope):
        identity = self._connections.get_identity(connection_id)
        if identity is not None:
            self._matchmaking_service.cancel(identity)

    async def _handle_create_room(self, connection_id, websocket, envelope):
        identity = self._connections.get_identity(connection_id)
        if identity is None:
            await self._send(websocket, schemas.make_envelope(
                protocol.ERROR, {"code": "NOT_LOGGED_IN"}, correlation_id=envelope["message_id"]))
            return

        room = self._room_service.create_room(identity)
        self._connections.set_room_id(connection_id, room.room_id)
        await self._send(websocket, schemas.make_envelope(
            protocol.ROOM_CREATED, {"room_id": room.room_id},
            correlation_id=envelope["message_id"]))

    async def _handle_join_room(self, connection_id, websocket, envelope):
        identity = self._connections.get_identity(connection_id)
        if identity is None:
            await self._send(websocket, schemas.make_envelope(
                protocol.ERROR, {"code": "NOT_LOGGED_IN"}, correlation_id=envelope["message_id"]))
            return

        room_id = envelope["payload"].get("room_id")
        try:
            role = self._room_service.join_room(room_id, identity)
        except RoomNotFoundError:
            await self._send(websocket, schemas.make_envelope(
                protocol.ERROR, {"code": "ROOM_NOT_FOUND"}, correlation_id=envelope["message_id"]))
            return
        except SpectatorCapExceededError:
            await self._send(websocket, schemas.make_envelope(
                protocol.ERROR, {"code": "SPECTATOR_CAP_EXCEEDED"},
                correlation_id=envelope["message_id"]))
            return

        self._connections.set_room_id(connection_id, room_id)

        # Sent immediately, before anything else: "black" and "spectator"
        # both otherwise start with an identical state_snapshot, and a
        # client has no other way to tell which one it just became -
        # whether to wait for a following game_started (black) or treat
        # the snapshot itself as the finish line (spectator).
        await self._send(websocket, schemas.make_envelope(
            protocol.ROOM_JOINED, {"role": role}, correlation_id=envelope["message_id"]))

        if role == "black":
            room = self._room_service.get_room(room_id)
            white_id = self._connections.find_connection_by_identity(room.white)
            if white_id is None:
                return  # the creator vanished before anyone joined - nothing to start
            session = await self._start_game(white_id, connection_id, rated=True)
            self._game_id_by_room_id[room_id] = session.game_id
            return

        # role == "spectator": the game is already running - catch up
        # with one full state_snapshot (Section 3.1's guarantee, same as
        # a fresh join or a reconnect), then receive every future
        # broadcast exactly like a player from here on.
        game_id = self._game_id_by_room_id.get(room_id)
        session = self._game_service.get_session(game_id) if game_id is not None else None
        if session is None:
            return
        self._connections.set_game_id(connection_id, game_id)
        await self._send(websocket, schemas.make_envelope(
            protocol.STATE_SNAPSHOT, dto.build_state_snapshot(session), game_id=game_id))

    async def _start_game(self, white_id, black_id, rated):
        session = self._game_service.create_session(
            white=self._connections.get_identity(white_id),
            black=self._connections.get_identity(black_id),
            rated=rated)

        self._connections.set_game_id(white_id, session.game_id)
        self._connections.set_game_id(black_id, session.game_id)

        snapshot_envelope = schemas.make_envelope(
            protocol.STATE_SNAPSHOT, dto.build_state_snapshot(session), game_id=session.game_id)
        await self._send(self._connections.get_socket(white_id), snapshot_envelope)
        await self._send(self._connections.get_socket(black_id), snapshot_envelope)
        return session

    async def _handle_move_request(self, connection_id, websocket, envelope):
        message_id = envelope["message_id"]
        cached_response = self._processed_move_requests.get(message_id)
        if cached_response is not None:
            await self._send(websocket, cached_response)
            return

        game_id = envelope["game_id"] or self._connections.get_game_id(connection_id)
        identity = self._connections.get_identity(connection_id)
        payload = envelope["payload"]

        result = await self._game_service.handle_move_request(
            game_id, identity,
            payload["from_row"], payload["from_col"], payload["to_row"], payload["to_col"])

        if result == "scheduled":
            session = self._game_service.get_session(game_id)
            response = schemas.make_envelope(
                protocol.MOVE_ACCEPTED, {"sequence": session.sequence if session else 0},
                game_id=game_id, correlation_id=message_id)
            # Only a genuinely scheduled move is cached: a rejected
            # attempt is harmless to reprocess (it just gets rejected
            # again), but an accepted one must never be scheduled twice.
            self._processed_move_requests[message_id] = response
            await self._send(websocket, response)
        # "rejected"/"game_not_found": MoveRejectedEvent (for a known
        # game) is published by GameService and delivered via
        # _on_move_rejected below; an unknown game_id has no session to
        # report through, so it is silently dropped here - a malformed
        # game_id this early is treated the same as a malformed message.

    async def _handle_jump_request(self, connection_id, websocket, envelope):
        game_id = envelope["game_id"] or self._connections.get_game_id(connection_id)
        identity = self._connections.get_identity(connection_id)
        payload = envelope["payload"]

        await self._game_service.handle_jump_request(game_id, identity, payload["row"], payload["col"])

    # ---------------------------------------------------------------
    # Phase F Milestone 1: periodic render-state push, called from
    # server_main.py's tick loop after each advance_time - not driven by
    # the ApplicationMessageBus like the events above, since this isn't a
    # domain occurrence, just a per-tick view of already-published state
    # (Section 3's board sync guarantee: the same payload, built once, is
    # sent to every connection in the game).
    # ---------------------------------------------------------------

    async def broadcast_render_state(self, game_id, session):
        await self._broadcast(game_id, schemas.make_envelope(
            protocol.RENDER_STATE, dto.build_render_state(session), game_id=game_id))

    # ---------------------------------------------------------------
    # Phase C: matchmaking clock, advanced by server_main.py's tick loop
    # independently of any specific game's activity (Decision 5's 1-
    # minute timeout keeps counting down even if every game is idle).
    # ---------------------------------------------------------------

    async def advance_matchmaking_clock(self, ms):
        self._matchmaking_clock_ms += ms
        matches, timed_out = self._matchmaking_service.tick(self._matchmaking_clock_ms)

        for white_identity, black_identity in matches:
            white_id = self._connections.find_connection_by_identity(white_identity)
            black_id = self._connections.find_connection_by_identity(black_identity)
            if white_id is None or black_id is None:
                continue  # disconnected between enqueue and match - drop silently
            await self._start_game(white_id, black_id, rated=True)

        for identity in timed_out:
            connection_id = self._connections.find_connection_by_identity(identity)
            if connection_id is None:
                continue
            await self._send(self._connections.get_socket(connection_id), schemas.make_envelope(
                protocol.MATCHMAKING_TIMEOUT, {}))

    # ---------------------------------------------------------------
    # Phase D: connection/reconnection clock, advanced by server_main.py's
    # tick loop independently of any specific game's activity - a
    # disconnected player's 20-second grace period keeps counting down
    # even if the game itself is currently idle.
    # ---------------------------------------------------------------

    async def advance_connection_clock(self, ms):
        self._connection_clock_ms += ms
        for game_id, identity in self._connection_service.pop_expired(self._connection_clock_ms):
            await self._game_service.forfeit(game_id, identity)

    # ---------------------------------------------------------------
    # ApplicationMessageBus -> outgoing server -> client messages
    #
    # Subscriptions run synchronously (ApplicationMessageBus.publish is
    # sync, same as GameEngine's own EventBus), but delivering a message
    # is I/O and must be awaited - each handler schedules its actual send
    # as a task rather than blocking the publisher. In production this
    # runs inside GameService.tick's own async context, which yields
    # control back to the event loop immediately after (the scheduled
    # task then runs before the next incoming message is processed); in
    # tests, awaiting websocket.recv() yields the same way.
    # ---------------------------------------------------------------

    def _on_game_started(self, event):
        asyncio.create_task(self._broadcast_game_started(event))

    async def _broadcast_game_started(self, event):
        session = self._game_service.get_session(event.game_id)
        if session is None:
            return
        payload = {
            "white": event.white, "black": event.black,
            "state_snapshot": dto.build_state_snapshot(session),
        }
        await self._broadcast(event.game_id, schemas.make_envelope(
            protocol.GAME_STARTED, payload, game_id=event.game_id))

    def _on_game_move_applied(self, event):
        asyncio.create_task(self._broadcast_move(event))

    async def _broadcast_move(self, event):
        session = self._game_service.get_session(event.game_id)
        if session is None:
            return
        session.next_sequence()
        payload = {
            "kind": "capture" if event.captured_piece is not None else "move",
            "from": [event.from_row, event.from_col],
            "to": [event.to_row, event.to_col],
            "moving_piece": str(event.moving_piece),
            "captured": str(event.captured_piece) if event.captured_piece is not None else None,
            "timestamp_ms": event.timestamp_ms,
            "sequence": session.sequence,
        }
        await self._broadcast(event.game_id, schemas.make_envelope(
            protocol.GAME_EVENT, payload, game_id=event.game_id))

    def _on_game_ended(self, event):
        asyncio.create_task(self._broadcast_game_ended(event))

    async def _broadcast_game_ended(self, event):
        await self._broadcast(event.game_id, schemas.make_envelope(
            protocol.GAME_OVER, {"winner": event.winner, "reason": event.reason},
            game_id=event.game_id))

    def _on_move_rejected(self, event):
        asyncio.create_task(self._send_move_rejected(event))

    async def _send_move_rejected(self, event):
        connection_id = self._find_connection(event.game_id, event.user_id)
        if connection_id is None:
            return
        await self._send(self._connections.get_socket(connection_id), schemas.make_envelope(
            protocol.MOVE_REJECTED, {"reason": event.reason}, game_id=event.game_id))

    def _find_connection(self, game_id, identity):
        for connection_id in self._connections.connections_in_game(game_id):
            if self._connections.get_identity(connection_id) == identity:
                return connection_id
        return None

    async def _broadcast(self, game_id, envelope):
        for connection_id in self._connections.connections_in_game(game_id):
            await self._send(self._connections.get_socket(connection_id), envelope)

    @staticmethod
    async def _send(websocket, envelope):
        if websocket is None:
            return
        try:
            await websocket.send(schemas.encode(envelope))
        except Exception:
            logger.exception("Failed to send %r to a connection", envelope.get("type"))
