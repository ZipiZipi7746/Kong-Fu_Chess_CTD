"""Accepts WebSocket connections, reads/writes JSON frames, delegates
every command to GameService/AuthenticationService - zero rule logic of
its own. Never imports kungfu_chess.model, kungfu_chess.rules,
kungfu_chess.realtime, or kungfu_chess.persistence.sqlite directly (the
architecture plan's forbidden-imports rule, Master Plan v2 Section 5);
board state only ever reaches this module already serialized, via
application.dto, and accounts only ever reach it through
AuthenticationService.

Phase A has no matchmaking or rooms yet: join_game's only supported mode
is "quick_local" - the first connection to request it waits, the second
pairs with it (first = White, second = Black) and a GameSession is
created immediately. Phases C/E replace this with real matchmaking/room
assignment without changing anything below the join_game handler itself.

Phase B replaces the password-less "connect" message with the permanent
CLI login flow (Decision 2): "register" creates an account, "login"
authenticates and returns a session token (Decision 7 - consumed fully
once Phase D adds reconnection). GameSession.color_for/white/black are
still plain display-name strings (unchanged from Phase A) - only the
identification step gained real credentials.
"""

import asyncio
import logging
import uuid

from kungfu_chess.application import dto
from kungfu_chess.application.auth_service import AuthenticationService, InvalidCredentialsError
from kungfu_chess.messaging.application_events import (
    GameStartedEvent,
    GameMoveAppliedEvent,
    MoveRejectedEvent,
    GameEndedEvent,
)
from kungfu_chess.persistence.repositories import DuplicateUsernameError
from kungfu_chess.server import schemas
from kungfu_chess.server.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class WebSocketGateway:
    def __init__(self, game_service, message_bus, connection_manager=None, auth_service=None):
        self._game_service = game_service
        self._message_bus = message_bus
        self._connections = connection_manager if connection_manager is not None else ConnectionManager()
        self._auth_service = auth_service if auth_service is not None else AuthenticationService()
        self._quick_local_waiting_connection_id = None

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
            self._connections.unregister(connection_id)

    # ---------------------------------------------------------------
    # Incoming client -> server messages
    # ---------------------------------------------------------------

    _HANDLER_NAMES = {
        "register": "_handle_register",
        "login": "_handle_login",
        "join_game": "_handle_join_game",
        "move_request": "_handle_move_request",
        "jump_request": "_handle_jump_request",
        "ping": "_handle_ping",
    }

    async def _dispatch(self, connection_id, websocket, raw):
        try:
            envelope = schemas.decode(raw)
        except schemas.MalformedMessageError as exc:
            await self._send(websocket, schemas.make_envelope(
                "error", {"code": "MALFORMED_MESSAGE", "message": str(exc)}))
            return

        handler_name = self._HANDLER_NAMES.get(envelope["type"])
        if handler_name is None:
            await self._send(websocket, schemas.make_envelope(
                "error", {"code": "UNKNOWN_MESSAGE_TYPE", "message": envelope["type"]},
                correlation_id=envelope["message_id"]))
            return

        await getattr(self, handler_name)(connection_id, websocket, envelope)

    async def _handle_register(self, connection_id, websocket, envelope):
        payload = envelope["payload"]
        try:
            self._auth_service.register(payload["username"], payload["password"])
        except DuplicateUsernameError:
            await self._send(websocket, schemas.make_envelope(
                "error", {"code": "USERNAME_TAKEN", "message": payload["username"]},
                correlation_id=envelope["message_id"]))
            return
        await self._send(websocket, schemas.make_envelope(
            "registered", {"username": payload["username"]},
            correlation_id=envelope["message_id"]))

    async def _handle_login(self, connection_id, websocket, envelope):
        payload = envelope["payload"]
        try:
            token = self._auth_service.login(payload["username"], payload["password"])
        except InvalidCredentialsError:
            await self._send(websocket, schemas.make_envelope(
                "error", {"code": "INVALID_CREDENTIALS"},
                correlation_id=envelope["message_id"]))
            return
        self._connections.set_identity(connection_id, payload["username"])
        self._connections.set_session_token(connection_id, token)
        await self._send(websocket, schemas.make_envelope(
            "login_ok", {"username": payload["username"], "session_token": token},
            correlation_id=envelope["message_id"]))

    async def _handle_ping(self, connection_id, websocket, envelope):
        await self._send(websocket, schemas.make_envelope(
            "pong", {}, correlation_id=envelope["message_id"]))

    async def _handle_join_game(self, connection_id, websocket, envelope):
        if self._quick_local_waiting_connection_id is None:
            self._quick_local_waiting_connection_id = connection_id
            return

        white_id = self._quick_local_waiting_connection_id
        black_id = connection_id
        self._quick_local_waiting_connection_id = None

        session = self._game_service.create_session(
            white=self._connections.get_identity(white_id),
            black=self._connections.get_identity(black_id))

        self._connections.set_game_id(white_id, session.game_id)
        self._connections.set_game_id(black_id, session.game_id)

        snapshot_envelope = schemas.make_envelope(
            "state_snapshot", dto.build_state_snapshot(session), game_id=session.game_id)
        await self._send(self._connections.get_socket(white_id), snapshot_envelope)
        await self._send(self._connections.get_socket(black_id), snapshot_envelope)

    async def _handle_move_request(self, connection_id, websocket, envelope):
        game_id = envelope["game_id"] or self._connections.get_game_id(connection_id)
        identity = self._connections.get_identity(connection_id)
        payload = envelope["payload"]

        result = await self._game_service.handle_move_request(
            game_id, identity,
            payload["from_row"], payload["from_col"], payload["to_row"], payload["to_col"])

        if result == "scheduled":
            session = self._game_service.get_session(game_id)
            await self._send(websocket, schemas.make_envelope(
                "move_accepted", {"sequence": session.sequence if session else 0},
                game_id=game_id, correlation_id=envelope["message_id"]))
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
            "render_state", dto.build_render_state(session), game_id=game_id))

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
            "game_started", payload, game_id=event.game_id))

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
            "game_event", payload, game_id=event.game_id))

    def _on_game_ended(self, event):
        asyncio.create_task(self._broadcast_game_ended(event))

    async def _broadcast_game_ended(self, event):
        await self._broadcast(event.game_id, schemas.make_envelope(
            "game_over", {"winner": event.winner, "reason": "king_capture"},
            game_id=event.game_id))

    def _on_move_rejected(self, event):
        asyncio.create_task(self._send_move_rejected(event))

    async def _send_move_rejected(self, event):
        connection_id = self._find_connection(event.game_id, event.user_id)
        if connection_id is None:
            return
        await self._send(self._connections.get_socket(connection_id), schemas.make_envelope(
            "move_rejected", {"reason": event.reason}, game_id=event.game_id))

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
