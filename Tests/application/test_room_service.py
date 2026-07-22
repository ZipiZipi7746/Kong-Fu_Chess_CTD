import pytest

from kungfu_chess.application.room_service import (
    Room,
    RoomNotFoundError,
    RoomService,
    SpectatorCapExceededError,
)


def make_fake_generator(*ids):
    """Returns a fixed sequence of room ids, one per call - lets tests
    drive RoomService's collision-retry logic deterministically instead
    of depending on real randomness."""
    sequence = list(ids)

    def generator():
        return sequence.pop(0)
    return generator


class TestCreateRoom:
    def test_creator_becomes_white(self):
        service = RoomService()
        room = service.create_room("alice")
        assert room.white == "alice"
        assert room.black is None
        assert room.spectators == []

    def test_returns_a_room_id_within_the_four_to_six_char_range(self):
        service = RoomService()
        room = service.create_room("alice")
        assert 4 <= len(room.room_id) <= 6

    def test_each_created_room_is_retrievable_by_id(self):
        service = RoomService()
        room = service.create_room("alice")
        assert service.get_room(room.room_id) is room

    def test_a_colliding_generated_id_is_retried(self):
        generator = make_fake_generator("AAAAA", "AAAAA", "BBBBB")
        service = RoomService(id_generator=generator)
        first = service.create_room("alice")
        second = service.create_room("bob")
        assert first.room_id == "AAAAA"
        assert second.room_id == "BBBBB"


class TestJoinRoom:
    def test_the_second_joiner_becomes_black(self):
        service = RoomService()
        room = service.create_room("alice")
        role = service.join_room(room.room_id, "bob")
        assert role == "black"
        assert room.black == "bob"

    def test_the_third_joiner_becomes_a_spectator(self):
        service = RoomService()
        room = service.create_room("alice")
        service.join_room(room.room_id, "bob")
        role = service.join_room(room.room_id, "carol")
        assert role == "spectator"
        assert room.spectators == ["carol"]

    def test_multiple_spectators_are_all_tracked(self):
        service = RoomService()
        room = service.create_room("alice")
        service.join_room(room.room_id, "bob")
        service.join_room(room.room_id, "carol")
        service.join_room(room.room_id, "dave")
        assert room.spectators == ["carol", "dave"]

    def test_joining_an_unknown_room_id_raises(self):
        service = RoomService()
        with pytest.raises(RoomNotFoundError):
            service.join_room("NOPE1", "alice")

    def test_the_21st_spectator_is_rejected(self):
        service = RoomService(spectator_cap=20)
        room = service.create_room("alice")
        service.join_room(room.room_id, "bob")
        for i in range(20):
            service.join_room(room.room_id, f"spectator{i}")

        with pytest.raises(SpectatorCapExceededError):
            service.join_room(room.room_id, "one_too_many")
        assert len(room.spectators) == 20


class TestLeaveRoom:
    def test_a_departing_player_frees_their_slot(self):
        service = RoomService()
        room = service.create_room("alice")
        service.join_room(room.room_id, "bob")
        service.leave_room(room.room_id, "bob")
        assert room.black is None

    def test_a_departing_spectator_is_removed(self):
        service = RoomService()
        room = service.create_room("alice")
        service.join_room(room.room_id, "bob")
        service.join_room(room.room_id, "carol")
        service.leave_room(room.room_id, "carol")
        assert room.spectators == []

    def test_the_room_survives_while_at_least_one_player_remains(self):
        service = RoomService()
        room = service.create_room("alice")
        service.join_room(room.room_id, "bob")
        service.leave_room(room.room_id, "bob")
        assert service.get_room(room.room_id) is room

    def test_the_room_is_torn_down_once_both_players_have_left(self):
        # Decision 9: spectators alone never keep a room alive.
        service = RoomService()
        room = service.create_room("alice")
        service.join_room(room.room_id, "bob")
        service.join_room(room.room_id, "carol")  # spectator

        service.leave_room(room.room_id, "alice")
        service.leave_room(room.room_id, "bob")

        assert service.get_room(room.room_id) is None

    def test_leaving_an_unknown_room_is_a_noop(self):
        service = RoomService()
        service.leave_room("NOPE1", "alice")  # must not raise
