"""The only module in this project that imports sqlite3 (Master Plan v2,
Section 10.1) - SqliteUserRepository/SqliteSessionRepository implement
the same UserRepository/SessionRepository contract as the in-memory
fakes (persistence/in_memory_repositories.py) and are exercised by the
identical repository contract test suite
(Tests/persistence/test_repository_contract.py), so a future call site
can swap one for the other without a behavior change.
"""

import sqlite3
from pathlib import Path

from kungfu_chess.persistence.repositories import (
    DuplicateUsernameError,
    Session,
    SessionRepository,
    User,
    UserRepository,
)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect(db_path=":memory:"):
    """Open a SQLite connection with the schema already applied - the
    single bootstrap entry point every caller (tests, server_main) should
    use instead of calling sqlite3.connect directly."""
    connection = sqlite3.connect(db_path)
    connection.executescript(_SCHEMA_PATH.read_text())
    connection.commit()
    return connection


class SqliteUserRepository(UserRepository):
    def __init__(self, connection):
        self._connection = connection

    def add(self, username, password_hash, password_salt, rating):
        try:
            cursor = self._connection.execute(
                "INSERT INTO users (username, password_hash, password_salt, rating) "
                "VALUES (?, ?, ?, ?)",
                (username, password_hash, password_salt, rating))
            self._connection.commit()
        except sqlite3.IntegrityError:
            raise DuplicateUsernameError(username)
        return self.get_by_id(cursor.lastrowid)

    def get_by_username(self, username):
        row = self._connection.execute(
            "SELECT user_id, username, password_hash, password_salt, rating "
            "FROM users WHERE username = ?", (username,)).fetchone()
        return self._to_user(row)

    def get_by_id(self, user_id):
        row = self._connection.execute(
            "SELECT user_id, username, password_hash, password_salt, rating "
            "FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return self._to_user(row)

    def update_rating(self, user_id, rating):
        self._connection.execute(
            "UPDATE users SET rating = ? WHERE user_id = ?", (rating, user_id))
        self._connection.commit()

    @staticmethod
    def _to_user(row):
        if row is None:
            return None
        user_id, username, password_hash, password_salt, rating = row
        return User(user_id=user_id, username=username, password_hash=password_hash,
                     password_salt=password_salt, rating=rating)


class SqliteSessionRepository(SessionRepository):
    def __init__(self, connection):
        self._connection = connection

    def create(self, token, user_id):
        self._connection.execute(
            "INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
        self._connection.commit()
        return Session(token=token, user_id=user_id)

    def get_by_token(self, token):
        row = self._connection.execute(
            "SELECT token, user_id FROM sessions WHERE token = ?", (token,)).fetchone()
        if row is None:
            return None
        token_, user_id = row
        return Session(token=token_, user_id=user_id)

    def delete(self, token):
        self._connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
        self._connection.commit()
