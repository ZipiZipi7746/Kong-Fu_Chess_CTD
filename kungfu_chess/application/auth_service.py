"""AuthenticationService (Master Plan v2, Section 10.1) - the sole owner
of password hashing and session-token issuance. Depends only on the
UserRepository/SessionRepository interfaces (persistence.repositories),
never on a concrete SQLite/in-memory implementation - the concrete
repository is injected, following this project's established
param=None -> real default DI convention (GameEngine, GameSession).

Passwords are hashed with PBKDF2-HMAC-SHA256 (Decision 3), a random
per-user salt, and a configurable iteration count - never stored or
compared as plaintext.
"""

import hashlib
import hmac
import secrets

from kungfu_chess.persistence.in_memory_repositories import (
    InMemorySessionRepository,
    InMemoryUserRepository,
)
from kungfu_chess.persistence.sqlite.sqlite_repositories import (
    SqliteSessionRepository,
    SqliteUserRepository,
    connect as _sqlite_connect,
)

DEFAULT_RATING = 1200
DEFAULT_PBKDF2_ITERATIONS = 390_000


class InvalidCredentialsError(Exception):
    """Raised by login() for an unknown username or a wrong password -
    deliberately the same error for both, so a failed login never
    reveals whether the username itself exists."""


class AuthenticationService:
    def __init__(self, user_repository=None, session_repository=None,
                 pbkdf2_iterations=DEFAULT_PBKDF2_ITERATIONS):
        self._users = user_repository if user_repository is not None else InMemoryUserRepository()
        self._sessions = session_repository if session_repository is not None else InMemorySessionRepository()
        self._pbkdf2_iterations = pbkdf2_iterations

    def register(self, username, password):
        salt = secrets.token_hex(16)
        password_hash = self._hash(password, salt)
        return self._users.add(username, password_hash, salt, DEFAULT_RATING)

    def login(self, username, password):
        user = self._users.get_by_username(username)
        if user is None or not self._verify(password, user.password_salt, user.password_hash):
            raise InvalidCredentialsError("invalid username or password")
        token = secrets.token_urlsafe(32)
        self._sessions.create(token, user.user_id)
        return token

    def get_user(self, username):
        return self._users.get_by_username(username)

    def resolve_token(self, token):
        session = self._sessions.get_by_token(token)
        if session is None:
            return None
        return self._users.get_by_id(session.user_id)

    def _hash(self, password, salt):
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt),
            self._pbkdf2_iterations).hex()

    def _verify(self, password, salt, expected_hash):
        return hmac.compare_digest(self._hash(password, salt), expected_hash)


def create_sqlite_backed_service(db_path, pbkdf2_iterations=DEFAULT_PBKDF2_ITERATIONS):
    """The composition root's way to get a real, file-persisted
    AuthenticationService (Master Plan v2 Section 5): server/server_main.py
    calls this instead of importing kungfu_chess.persistence.sqlite
    directly, which the import-boundary rule forbids for any server/
    module - only application/ is allowed to depend on persistence/.

    Returns (auth_service, user_repository) - the repository is exposed
    too so the composition root can inject the *same* UserRepository
    into GameService (Phase C rating application needs to see the exact
    accounts AuthenticationService just registered/logged in, not a
    second, disconnected in-memory copy)."""
    connection = _sqlite_connect(db_path)
    user_repository = SqliteUserRepository(connection)
    auth_service = AuthenticationService(
        user_repository, SqliteSessionRepository(connection),
        pbkdf2_iterations=pbkdf2_iterations)
    return auth_service, user_repository
