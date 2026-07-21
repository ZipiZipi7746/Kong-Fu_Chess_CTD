"""A real, non-persistent implementation of the repository interfaces -
the default fake used by tests and by AuthenticationService before
SQLite is wired into server_main.py. Not a mock: it implements the full
UserRepository/SessionRepository contract for real, just backed by a
dict instead of a database (see the repository contract test suite,
which runs the exact same tests against this and the SQLite
implementation).
"""

import itertools

from kungfu_chess.persistence.repositories import (
    DuplicateUsernameError,
    Session,
    SessionRepository,
    User,
    UserRepository,
)


class InMemoryUserRepository(UserRepository):
    def __init__(self):
        self._by_id = {}
        self._by_username = {}
        self._id_counter = itertools.count(1)

    def add(self, username, password_hash, password_salt, rating):
        if username in self._by_username:
            raise DuplicateUsernameError(username)
        user = User(user_id=next(self._id_counter), username=username,
                    password_hash=password_hash, password_salt=password_salt,
                    rating=rating)
        self._by_id[user.user_id] = user
        self._by_username[username] = user
        return user

    def get_by_username(self, username):
        return self._by_username.get(username)

    def get_by_id(self, user_id):
        return self._by_id.get(user_id)

    def update_rating(self, user_id, rating):
        user = self._by_id[user_id]
        updated = User(user_id=user.user_id, username=user.username,
                        password_hash=user.password_hash,
                        password_salt=user.password_salt, rating=rating)
        self._by_id[user_id] = updated
        self._by_username[user.username] = updated


class InMemorySessionRepository(SessionRepository):
    def __init__(self):
        self._sessions = {}

    def create(self, token, user_id):
        session = Session(token=token, user_id=user_id)
        self._sessions[token] = session
        return session

    def get_by_token(self, token):
        return self._sessions.get(token)

    def delete(self, token):
        self._sessions.pop(token, None)
