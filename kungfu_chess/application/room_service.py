"""RoomService (Master Plan v2 Section 10.4, Decisions 8/9) - room
lifecycle: create_room/join_room/leave_room. Room-ID generation lives
in its own small free function, injectable via id_generator, so the
code scheme (Decision 8: a short human-readable alphanumeric code, not
a UUID) can change independently of the room-membership logic below,
and so tests can drive collision-retry deterministically instead of
depending on real randomness.

Roles: the creator is White; the second joiner is Black; everyone
after that is a read-only spectator, capped at DEFAULT_SPECTATOR_CAP
(Decision 9). A room is torn down immediately once both players have
left - spectators alone never keep a room alive. Room teardown here is
purely lobby/invite-code bookkeeping: it does not end the underlying
GameSession itself - that is already fully handled by Phase D's
per-player disconnect grace period/forfeit (see connection_service.py),
independently of whether a room-level entry still exists.
"""

import random
import string

DEFAULT_SPECTATOR_CAP = 20
ROOM_ID_LENGTH = 5
ROOM_ID_ALPHABET = string.ascii_uppercase + string.digits


def _random_room_id():
    return "".join(random.choices(ROOM_ID_ALPHABET, k=ROOM_ID_LENGTH))


class RoomNotFoundError(Exception):
    pass


class SpectatorCapExceededError(Exception):
    pass


class Room:
    def __init__(self, room_id, white):
        self.room_id = room_id
        self.white = white
        self.black = None
        self.spectators = []

    def has_no_players(self):
        return self.white is None and self.black is None


class RoomService:
    def __init__(self, spectator_cap=DEFAULT_SPECTATOR_CAP, id_generator=None):
        self._spectator_cap = spectator_cap
        self._id_generator = id_generator if id_generator is not None else _random_room_id
        self._rooms = {}

    def create_room(self, creator_identity):
        room_id = self._generate_unique_room_id()
        room = Room(room_id, creator_identity)
        self._rooms[room_id] = room
        return room

    def join_room(self, room_id, identity):
        """Returns the assigned role: "black" (the second player) or
        "spectator". Raises RoomNotFoundError / SpectatorCapExceededError."""
        room = self._rooms.get(room_id)
        if room is None:
            raise RoomNotFoundError(room_id)

        if room.black is None:
            room.black = identity
            return "black"

        if len(room.spectators) >= self._spectator_cap:
            raise SpectatorCapExceededError(room_id)

        room.spectators.append(identity)
        return "spectator"

    def leave_room(self, room_id, identity):
        room = self._rooms.get(room_id)
        if room is None:
            return

        if room.white == identity:
            room.white = None
        elif room.black == identity:
            room.black = None
        elif identity in room.spectators:
            room.spectators.remove(identity)

        if room.has_no_players():
            del self._rooms[room_id]

    def get_room(self, room_id):
        return self._rooms.get(room_id)

    def _generate_unique_room_id(self):
        while True:
            room_id = self._id_generator()
            if room_id not in self._rooms:
                return room_id
