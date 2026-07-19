import asyncio
import contextlib
import json

import pytest
import websockets

from kungfu_chess.model.piece import Piece
from kungfu_chess.messaging.application_message_bus import ApplicationMessageBus
from kungfu_chess.application.game_service import GameService
from kungfu_chess.server.websocket_gateway import WebSocketGateway
from kungfu_chess.server import schemas


RECV_TIMEOUT = 2.0


@contextlib.asynccontextmanager
async def running_gateway():
    bus = ApplicationMessageBus()
    service = GameService(bus)
    gateway = WebSocketGateway(service, bus)
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


class TestConnectAndJoin:
    @pytest.mark.asyncio
    async def test_first_connector_becomes_white_second_becomes_black(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await send(white_ws, "connect", {"username": "alice"})
                await send(black_ws, "connect", {"username": "bob"})
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
                await send(white_ws, "connect", {"username": "alice"})
                await send(black_ws, "connect", {"username": "bob"})
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
                await send(white_ws, "connect", {"username": "alice"})
                await send(black_ws, "connect", {"username": "bob"})
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
                await send(white_ws, "connect", {"username": "alice"})
                await send(black_ws, "connect", {"username": "bob"})
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
                assert black_event["type"] == "game_event"

    @pytest.mark.asyncio
    async def test_wrong_color_move_is_rejected_to_the_requester_only(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await send(white_ws, "connect", {"username": "alice"})
                await send(black_ws, "connect", {"username": "bob"})
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
                await send(white_ws, "connect", {"username": "alice"})
                await send(black_ws, "connect", {"username": "bob"})
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
                await send(white_ws, "connect", {"username": "alice"})
                await send(black_ws, "connect", {"username": "bob"})
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


class TestDisconnection:
    @pytest.mark.asyncio
    async def test_disconnecting_while_waiting_for_a_quick_local_opponent_frees_the_slot(self):
        async with running_gateway() as (gateway, service, url):
            async with websockets.connect(url) as first_ws:
                await send(first_ws, "connect", {"username": "alice"})
                await send(first_ws, "join_game", {"mode": "quick_local"})
                await asyncio.sleep(0.05)  # let the server process before disconnecting
                assert gateway._quick_local_waiting_connection_id is not None

            await asyncio.sleep(0.05)  # let the server observe the close
            assert gateway._quick_local_waiting_connection_id is None

            # A fresh pair can still be matched afterward - the freed
            # slot isn't left permanently stuck "waiting".
            async with websockets.connect(url) as white_ws, websockets.connect(url) as black_ws:
                await send(white_ws, "connect", {"username": "carol"})
                await send(black_ws, "connect", {"username": "dave"})
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
