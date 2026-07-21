"""Repository interfaces (Master Plan v2, Section 9/10.1) - the only
contract application/auth_service.py depends on. Two implementations
exist: InMemoryUserRepository/InMemorySessionRepository
(persistence/in_memory_repositories.py, used by tests and any
environment without SQLite wired in yet) and
SqliteUserRepository/SqliteSessionRepository
(persistence/sqlite/sqlite_repositories.py, the only place sqlite3 is
imported anywhere in this project). Both are exercised by the same
repository contract test suite (Tests/persistence/test_repository_
contract.py) so a future swap can't silently change behavior.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class DuplicateUsernameError(Exception):
    """Raised by UserRepository.add() when the username is already taken."""


@dataclass(frozen=True)
class User:
    user_id: int
    username: str
    password_hash: str
    password_salt: str
    rating: int


@dataclass(frozen=True)
class Session:
    token: str
    user_id: int


class UserRepository(ABC):
    @abstractmethod
    def add(self, username, password_hash, password_salt, rating):
        """Create and return a new User. Raises DuplicateUsernameError if
        username is already taken."""

    @abstractmethod
    def get_by_username(self, username):
        """Return the User, or None if no such username exists."""

    @abstractmethod
    def get_by_id(self, user_id):
        """Return the User, or None if no such user_id exists."""

    @abstractmethod
    def update_rating(self, user_id, rating):
        """Persist a new rating value for an existing user."""


class SessionRepository(ABC):
    @abstractmethod
    def create(self, token, user_id):
        """Create and return a new Session bound to user_id."""

    @abstractmethod
    def get_by_token(self, token):
        """Return the Session, or None if the token is unknown."""

    @abstractmethod
    def delete(self, token):
        """Remove a session (e.g. on logout); a no-op if already gone."""
