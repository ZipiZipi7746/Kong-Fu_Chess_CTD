import pytest

from kungfu_chess.model.board import Board
from kungfu_chess.messaging.application_message_bus import ApplicationMessageBus
from kungfu_chess.messaging.application_events import (
    GameStartedEvent,
    GameMoveAppliedEvent,
    MoveRejectedEvent,
    GameEndedEvent,
)
from kungfu_chess.application.game_service import GameService


def make_service():
    bus = ApplicationMessageBus()
    service = GameService(bus)
    return service, bus


def subscribe(bus, event_type):
    received = []
    bus.subscribe(event_type, received.append)
    return received


class TestCreateSession:
    def test_returns_a_session_with_the_standard_starting_position(self):
        service, bus = make_service()
        session = service.create_session(white="alice", black="bob")
        assert session.engine.board.get_cell(0, 4).kind == "K"
        assert session.engine.board.get_cell(0, 4).color == "b"
        assert session.engine.board.get_cell(7, 4).kind == "K"
        assert session.engine.board.get_cell(7, 4).color == "w"

    def test_publishes_game_started_event(self):
        service, bus = make_service()
        received = subscribe(bus, GameStartedEvent)

        session = service.create_session(white="alice", black="bob")

        assert len(received) == 1
        assert received[0].game_id == session.game_id
        assert received[0].white == "alice"
        assert received[0].black == "bob"

    def test_each_session_gets_a_unique_game_id(self):
        service, bus = make_service()
        first = service.create_session(white="alice", black="bob")
        second = service.create_session(white="carol", black="dave")
        assert first.game_id != second.game_id

    def test_created_session_is_retrievable_by_id(self):
        service, bus = make_service()
        session = service.create_session(white="alice", black="bob")
        assert service.get_session(session.game_id) is session

    def test_unknown_game_id_returns_none(self):
        service, bus = make_service()
        assert service.get_session("nonexistent") is None

    def test_sessions_returns_every_created_session_keyed_by_game_id(self):
        service, bus = make_service()
        first = service.create_session(white="alice", black="bob")
        second = service.create_session(white="carol", black="dave")
        assert service.sessions() == {first.game_id: first, second.game_id: second}

    def test_sessions_returns_a_copy_not_the_live_registry(self):
        # The tick loop (server_main.py) iterates this while sessions may
        # be concurrently added elsewhere - a live reference would risk a
        # "dictionary changed size during iteration" error.
        service, bus = make_service()
        service.create_session(white="alice", black="bob")
        snapshot = service.sessions()
        service.create_session(white="carol", black="dave")
        assert len(snapshot) == 1

    def test_an_injected_board_overrides_the_standard_starting_position(self):
        # DI point used throughout the rest of this file for small,
        # focused boards - matching GameEngine's own test style - rather
        # than always exercising the full standard opening.
        service, bus = make_service()
        session = service.create_session(white="alice", black="bob", board=Board([["wR", "."]]))
        assert session.engine.board.get_cell(0, 0).kind == "R"
        assert session.engine.board.rows == 1


class TestHandleMoveRequest:
    @pytest.mark.asyncio
    async def test_legal_move_by_the_owning_color_is_scheduled(self):
        service, bus = make_service()
        session = service.create_session(
            white="alice", black="bob", board=Board([["wR", "."]]))

        result = await service.handle_move_request(session.game_id, "alice", 0, 0, 0, 1)

        assert result == "scheduled"

    @pytest.mark.asyncio
    async def test_wrong_color_move_is_rejected_and_board_unchanged(self):
        service, bus = make_service()
        session = service.create_session(
            white="alice", black="bob", board=Board([["wR", "."]]))
        received = subscribe(bus, MoveRejectedEvent)

        result = await service.handle_move_request(
            session.game_id, "bob", 0, 0, 0, 1)  # bob (black) does not own wR

        assert result == "rejected"
        assert len(received) == 1
        assert received[0].game_id == session.game_id
        assert received[0].user_id == "bob"
        assert received[0].reason == "NOT_YOUR_TURN_OR_ACTION"
        assert session.engine.board.get_cell(0, 0).kind == "R"  # never moved

    @pytest.mark.asyncio
    async def test_structurally_illegal_move_is_rejected(self):
        service, bus = make_service()
        session = service.create_session(
            white="alice", black="bob", board=Board([["wR", "."], [".", "."]]))
        received = subscribe(bus, MoveRejectedEvent)

        result = await service.handle_move_request(
            session.game_id, "alice", 0, 0, 1, 1)  # diagonal, illegal for a rook

        assert result == "rejected"
        assert received[0].reason == "INVALID_MOVE"

    @pytest.mark.asyncio
    async def test_unknown_game_id_returns_game_not_found(self):
        service, bus = make_service()
        result = await service.handle_move_request("nonexistent", "alice", 0, 0, 0, 1)
        assert result == "game_not_found"


class TestHandleJumpRequest:
    @pytest.mark.asyncio
    async def test_legal_jump_by_the_owning_color_succeeds(self):
        service, bus = make_service()
        session = service.create_session(
            white="alice", black="bob", board=Board([["wR"]]))

        result = await service.handle_jump_request(session.game_id, "alice", 0, 0)

        assert result is True
        assert session.engine.is_airborne(0, 0) is True

    @pytest.mark.asyncio
    async def test_wrong_color_jump_is_rejected(self):
        service, bus = make_service()
        session = service.create_session(
            white="alice", black="bob", board=Board([["wR"]]))
        received = subscribe(bus, MoveRejectedEvent)

        result = await service.handle_jump_request(session.game_id, "bob", 0, 0)

        assert result is False
        assert received[0].reason == "NOT_YOUR_TURN_OR_ACTION"
        assert session.engine.is_airborne(0, 0) is False


class TestTickTranslatesDomainEventsToApplicationEvents:
    @pytest.mark.asyncio
    async def test_a_resolved_move_publishes_game_move_applied_event(self):
        service, bus = make_service()
        session = service.create_session(
            white="alice", black="bob", board=Board([["wR", "."]]))
        received = subscribe(bus, GameMoveAppliedEvent)

        await service.handle_move_request(session.game_id, "alice", 0, 0, 0, 1)
        await service.tick(session.game_id, 1000)  # 1 cell, arrives at 1000ms

        assert len(received) == 1
        assert received[0].game_id == session.game_id
        assert (received[0].from_row, received[0].from_col) == (0, 0)
        assert (received[0].to_row, received[0].to_col) == (0, 1)

    @pytest.mark.asyncio
    async def test_a_king_capture_publishes_game_ended_event(self):
        service, bus = make_service()
        session = service.create_session(
            white="alice", black="bob", board=Board([["wR", "bK"]]))
        received = subscribe(bus, GameEndedEvent)

        await service.handle_move_request(session.game_id, "alice", 0, 0, 0, 1)
        await service.tick(session.game_id, 1000)  # 1 cell, arrives at 1000ms

        assert len(received) == 1
        assert received[0].game_id == session.game_id
        assert received[0].winner == "w"

    @pytest.mark.asyncio
    async def test_tick_on_unknown_game_id_is_a_noop(self):
        service, bus = make_service()
        await service.tick("nonexistent", 1000)  # must not raise
