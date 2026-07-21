import asyncio
import contextlib
import json

import pytest
import websockets

from kungfu_chess.model.piece import Piece
from kungfu_chess.messaging.application_message_bus import ApplicationMessageBus
from kungfu_chess.application.auth_service import AuthenticationService
from kungfu_chess.application.game_service import GameService
from kungfu_chess.persistence.in_memory_repositories import InMemoryUserRepository
from kungfu_chess.server.websocket_gateway import WebSocketGateway
from kungfu_chess.server import schemas


RECV_TIMEOUT = 2.0

# A low iteration count keeps this suite fast - AuthenticationService's
# real default cost (Decision 3) is exercised by Tests/application/
# test_auth_service.py, not needed again here.
_FAST_ITERATIONS = 10


@contextlib.asynccontextmanager
async def running_gateway():
    bus = ApplicationMessageBus()
    # Shared between auth and game services, exactly as server_main.py's
    # composition root shares them - a rated game's rating lookups
    # (GameService._apply_rating) need to see the same accounts
    # AuthenticationService just registered/logged in.
    user_repository = InMemoryUserRepository()
    service = GameService(bus, user_repository=user_repository)
    auth_service = AuthenticationService(user_repository, pbkdf2_iterations=_FAST_ITERATIONS)
    gateway = WebSocketGateway(service, bus, auth_service=auth_service)
    # Bound to the literal IPv4 loopback address, not "localhost" - which
    # host "localhost" resolves to (127.0.0.1 vs. ::1) is not guaranteed
    # stable across environments/runs, and an IPv6 host needs bracket
    # syntax ("ws://[::1]:port") that a plain f-string doesn't produce.
    async with websockets.serve(gateway.handle_connection, "127.0.0.1", 0) as server:
        _, port = server.sockets[0].getsockname()[:2]
        yield gateway, service, f"ws://127.0.0.1:{port}"


async def send(websocket, type_, payload, **kwargs):
    await websocket.send(schemas.encode(schemas.make_envelope(type_, payload, **kwargs)))


async def recv(websocket):
    raw = await asyncio.wait_for(websocket.recv(), timeout=RECV_TIMEOUT)
    return json.loads(raw)


async def register_and_login(websocket, username, password="pw"):
    """The Phase B CLI login flow (Decision 2), collapsed into one helper
    for every test below that just needs "some authenticated player" -
    register then login, discarding both acknowledgements. Authentication
    itself is exercised directly by TestAuthentication."""
    await send(websocket, "register", {"username": username, "password": password})
    await recv(websocket)  # registered
    await send(websocket, "login", {"username": username, "password": password})
    return await recv(websocket)  # login_ok


class TestAuthentication:
    @pytest.mark.asyncio
    async def test_registering_a_new_username_succeeds(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as ws:
                await send(ws, "register", {"username": "alice", "password": "pw"})
                response = await recv(ws)
                assert response["type"] == "registered"
                assert response["payload"]["username"] == "alice"

    @pytest.mark.asyncio
    async def test_registering_a_taken_username_is_rejected_cleanly(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as first_ws, websockets.connect(url) as second_ws:
                await send(first_ws, "register", {"username": "alice", "password": "pw1"})
                await recv(first_ws)

                await send(second_ws, "register", {"username": "alice", "password": "pw2"})
                response = await recv(second_ws)
                assert response["type"] == "error"
                assert response["payload"]["code"] == "USERNAME_TAKEN"

    @pytest.mark.asyncio
    async def test_login_with_correct_credentials_returns_a_session_token(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as ws:
                await send(ws, "register", {"username": "alice", "password": "correct"})
                await recv(ws)

                await send(ws, "login", {"username": "alice", "password": "correct"})
                response = await recv(ws)
                assert response["type"] == "login_ok"
                assert response["payload"]["username"] == "alice"
                assert response["payload"]["session_token"]

    @pytest.mark.asyncio
    async def test_login_with_wrong_password_is_rejected_cleanly(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as ws:
                await send(ws, "register", {"username": "alice", "password": "correct"})
                await recv(ws)

                await send(ws, "login", {"username": "alice", "password": "wrong"})
                response = await recv(ws)
                assert response["type"] == "error"
                assert response["payload"]["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_with_unknown_username_is_rejected_cleanly(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as ws:
                await send(ws, "login", {"username": "nobody", "password": "whatever"})
                response = await recv(ws)
                assert response["type"] == "error"
                assert response["payload"]["code"] == "INVALID_CREDENTIALS"


class TestConnectAndJoin:
    @pytest.mark.asyncio
    async def test_first_connector_becomes_white_second_becomes_black(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})

                white_snapshot = await recv(white_ws)
                black_snapshot = await recv(black_ws)

                assert white_snapshot["type"] == "state_snapshot"
                assert black_snapshot["type"] == "state_snapshot"
                assert white_snapshot["game_id"] == black_snapshot["game_id"]

                game_id = white_snapshot["game_id"]
                session = service.get_session(game_id)
                assert session.white == "alice"
                assert session.black == "bob"

    @pytest.mark.asyncio
    async def test_state_snapshot_carries_the_standard_starting_board_at_sequence_zero(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})

                snapshot = await recv(white_ws)
                await recv(black_ws)

                assert snapshot["payload"]["board"][0][4] == "bK"
                assert snapshot["payload"]["board"][7][4] == "wK"
                assert snapshot["payload"]["sequence"] == 0

    @pytest.mark.asyncio
    async def test_both_players_receive_game_started(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})

                await recv(white_ws)  # state_snapshot
                await recv(black_ws)  # state_snapshot
                white_started = await recv(white_ws)
                black_started = await recv(black_ws)

                assert white_started["type"] == "game_started"
                assert white_started["payload"]["white"] == "alice"
                assert white_started["payload"]["black"] == "bob"
                assert black_started["type"] == "game_started"


class TestMoveFlow:
    @pytest.mark.asyncio
    async def test_legal_move_is_accepted_and_broadcast_to_both_players(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})
                await recv(white_ws)
                await recv(black_ws)
                await recv(white_ws)
                game_started = await recv(black_ws)
                game_id = game_started["game_id"]

                await send(white_ws, "move_request",
                           {"from_row": 6, "from_col": 4, "to_row": 5, "to_col": 4},
                           game_id=game_id)

                accepted = await recv(white_ws)
                assert accepted["type"] == "move_accepted"

                await service.tick(game_id, 1000)  # 1 cell, arrives at 1000ms

                white_event = await recv(white_ws)
                black_event = await recv(black_ws)
                assert white_event["type"] == "game_event"
                assert white_event["payload"]["from"] == [6, 4]
                assert white_event["payload"]["to"] == [5, 4]
                assert white_event["payload"]["moving_piece"] == "wP"
                assert white_event["payload"]["timestamp_ms"] == 1000
                assert black_event["type"] == "game_event"

    @pytest.mark.asyncio
    async def test_wrong_color_move_is_rejected_to_the_requester_only(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})
                await recv(white_ws)
                black_snapshot = await recv(black_ws)
                await recv(white_ws)
                await recv(black_ws)
                game_id = black_snapshot["game_id"]

                # bob (black) tries to move a white pawn
                await send(black_ws, "move_request",
                           {"from_row": 6, "from_col": 4, "to_row": 5, "to_col": 4},
                           game_id=game_id)

                rejected = await recv(black_ws)
                assert rejected["type"] == "move_rejected"
                assert rejected["payload"]["reason"] == "NOT_YOUR_TURN_OR_ACTION"

    @pytest.mark.asyncio
    async def test_king_capture_broadcasts_game_over_to_both_players(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})
                white_snapshot = await recv(white_ws)
                await recv(black_ws)
                await recv(white_ws)
                await recv(black_ws)
                game_id = white_snapshot["game_id"]

                # Reach into the just-created session's board and place a
                # white rook one square below the black King, clearing a
                # capture setup that doesn't require playing out a full
                # opening - the same technique GameEngine's own tests use.
                session = service.get_session(game_id)
                session.engine.board.set_cell(1, 4, Piece("w", "R"))

                await send(white_ws, "move_request",
                           {"from_row": 1, "from_col": 4, "to_row": 0, "to_col": 4},
                           game_id=game_id)
                await recv(white_ws)  # move_accepted

                await service.tick(game_id, 1000)  # 1 cell, arrives at 1000ms

                await recv(white_ws)  # game_event (the capture)
                await recv(black_ws)  # game_event (the capture)
                white_over = await recv(white_ws)
                black_over = await recv(black_ws)

                assert white_over["type"] == "game_over"
                assert white_over["payload"]["winner"] == "w"
                assert black_over["type"] == "game_over"
                assert black_over["payload"]["winner"] == "w"

    @pytest.mark.asyncio
    async def test_legal_jump_by_the_owning_color_makes_the_piece_airborne(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})
                white_snapshot = await recv(white_ws)
                await recv(black_ws)
                await recv(white_ws)
                await recv(black_ws)
                game_id = white_snapshot["game_id"]

                await send(white_ws, "jump_request", {"row": 6, "col": 4}, game_id=game_id)

                session = service.get_session(game_id)
                for _ in range(50):
                    if session.engine.is_airborne(6, 4):
                        break
                    await asyncio.sleep(0.01)
                assert session.engine.is_airborne(6, 4) is True


class TestBoardSynchronization:
    """Master Plan v2, Section 3.4: both connected clients must always
    observe byte-for-byte identical state - never independently-computed,
    "close enough" views of the same game. This is a regression gate: any
    future change to _broadcast/_handle_join_game/dto.build_state_snapshot
    that lets the two payloads diverge must fail this test."""

    @pytest.mark.asyncio
    async def test_both_players_receive_an_identical_state_snapshot_on_join(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})

                white_snapshot = await recv(white_ws)
                black_snapshot = await recv(black_ws)

                assert white_snapshot["payload"] == black_snapshot["payload"]
                assert white_snapshot["game_id"] == black_snapshot["game_id"]

    @pytest.mark.asyncio
    async def test_both_players_receive_an_identical_game_event_for_the_same_move(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})
                white_snapshot = await recv(white_ws)
                await recv(black_ws)
                await recv(white_ws)  # game_started
                game_started = await recv(black_ws)
                game_id = game_started["game_id"]

                await send(white_ws, "move_request",
                           {"from_row": 6, "from_col": 4, "to_row": 5, "to_col": 4},
                           game_id=game_id)
                await recv(white_ws)  # move_accepted

                await service.tick(game_id, 1000)  # 1 cell, arrives at 1000ms

                white_event = await recv(white_ws)
                black_event = await recv(black_ws)

                assert white_event["payload"] == black_event["payload"]
                assert white_event["payload"]["sequence"] == white_snapshot["payload"]["sequence"] + 1


class TestRenderStateBroadcast:
    """Phase F Milestone 1: the networked GUI client animates from this
    periodic broadcast. Same Section 3.4 guarantee as everything else -
    both connected clients get the identical payload."""

    @pytest.mark.asyncio
    async def test_broadcast_render_state_sends_an_identical_payload_to_both_players(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})
                white_snapshot = await recv(white_ws)
                await recv(black_ws)
                await recv(white_ws)  # game_started
                await recv(black_ws)  # game_started
                game_id = white_snapshot["game_id"]

                session = service.get_session(game_id)
                await gateway.broadcast_render_state(game_id, session)

                white_render_state = await recv(white_ws)
                black_render_state = await recv(black_ws)

                assert white_render_state["type"] == "render_state"
                assert white_render_state["payload"] == black_render_state["payload"]
                assert white_render_state["payload"]["motions"] == []

    @pytest.mark.asyncio
    async def test_broadcast_render_state_reports_an_in_flight_motion(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})
                white_snapshot = await recv(white_ws)
                await recv(black_ws)
                await recv(white_ws)
                await recv(black_ws)
                game_id = white_snapshot["game_id"]

                await send(white_ws, "move_request",
                           {"from_row": 6, "from_col": 4, "to_row": 5, "to_col": 4},
                           game_id=game_id)
                await recv(white_ws)  # move_accepted

                session = service.get_session(game_id)
                await gateway.broadcast_render_state(game_id, session)

                render_state = await recv(white_ws)
                assert render_state["payload"]["motions"] == [
                    {"from": [6, 4], "to": [5, 4], "progress": 0.0}]


class TestMatchmaking:
    """Master Plan v2 Section 10.2/Decision 5/13: the "play" queue,
    separate from quick_local (which stays available for local/offline-
    style testing - see websocket_gateway.py's module docstring)."""

    @pytest.mark.asyncio
    async def test_two_players_within_rating_band_get_matched_and_started(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")

                await send(white_ws, "play", {})
                await recv(white_ws)  # searching_match
                await send(black_ws, "play", {})
                await recv(black_ws)  # searching_match
                await gateway.advance_matchmaking_clock(100)

                white_snapshot = await recv(white_ws)
                black_snapshot = await recv(black_ws)
                assert white_snapshot["type"] == "state_snapshot"
                assert black_snapshot["type"] == "state_snapshot"
                assert white_snapshot["game_id"] == black_snapshot["game_id"]

                game_id = white_snapshot["game_id"]
                session = service.get_session(game_id)
                assert session.rated is True
                assert session.white == "alice"
                assert session.black == "bob"

    @pytest.mark.asyncio
    async def test_a_lone_player_receives_no_match_until_a_second_arrives(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as ws:
                await register_and_login(ws, "alice")
                await send(ws, "play", {})
                await recv(ws)  # searching_match
                await gateway.advance_matchmaking_clock(100)
                # Nothing should have arrived yet - assert via a ping/pong
                # round trip instead of a fixed sleep-then-check.
                await send(ws, "ping", {})
                pong = await recv(ws)
                assert pong["type"] == "pong"

    @pytest.mark.asyncio
    async def test_cancel_matchmaking_removes_a_waiting_player(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "alice")
                await register_and_login(black_ws, "bob")

                await send(white_ws, "play", {})
                await recv(white_ws)  # searching_match
                await send(white_ws, "cancel_matchmaking", {})
                await send(black_ws, "play", {})
                await recv(black_ws)  # searching_match
                await gateway.advance_matchmaking_clock(100)

                # alice cancelled, so no match should have happened for
                # bob either - confirm via ping/pong rather than a sleep.
                await send(black_ws, "ping", {})
                pong = await recv(black_ws)
                assert pong["type"] == "pong"

    @pytest.mark.asyncio
    async def test_a_player_who_times_out_is_notified_and_can_search_again(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as ws:
                await register_and_login(ws, "alice")
                await send(ws, "play", {})
                await recv(ws)  # searching_match
                await gateway.advance_matchmaking_clock(60_000)

                timeout_msg = await recv(ws)
                assert timeout_msg["type"] == "matchmaking_timeout"


class TestDisconnection:
    @pytest.mark.asyncio
    async def test_disconnecting_while_waiting_for_a_quick_local_opponent_frees_the_slot(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as first_ws:
                await register_and_login(first_ws, "alice")
                await send(first_ws, "join_game", {"mode": "quick_local"})
                await asyncio.sleep(0.05)  # let the server process before disconnecting
                assert gateway._quick_local_waiting_connection_id is not None

            await asyncio.sleep(0.05)  # let the server observe the close
            assert gateway._quick_local_waiting_connection_id is None

            # A fresh pair can still be matched afterward - the freed
            # slot isn't left permanently stuck "waiting".
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await register_and_login(white_ws, "carol")
                await register_and_login(black_ws, "dave")
                await send(white_ws, "join_game", {"mode": "quick_local"})
                await send(black_ws, "join_game", {"mode": "quick_local"})
                snapshot = await recv(white_ws)
                assert snapshot["type"] == "state_snapshot"


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_malformed_message_receives_an_error_without_closing_the_connection(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as ws:
                await ws.send("not json")
                error = await recv(ws)
                assert error["type"] == "error"
                assert error["payload"]["code"] == "MALFORMED_MESSAGE"

                # connection still open and usable afterward
                await send(ws, "ping", {})
                pong = await recv(ws)
                assert pong["type"] == "pong"

    @pytest.mark.asyncio
    async def test_unknown_message_type_receives_an_error(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as ws:
                await send(ws, "not_a_real_type", {})
                error = await recv(ws)
                assert error["type"] == "error"
                assert error["payload"]["code"] == "UNKNOWN_MESSAGE_TYPE"
