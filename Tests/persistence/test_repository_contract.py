"""Master Plan v2, Section 10.1: the same test suite run against every
UserRepository/SessionRepository implementation via the repository()
fixture each subclass provides, so a future SQLite swap can't silently
behave differently from the in-memory fake. TestInMemory* below runs it
against InMemoryUserRepository/InMemorySessionRepository; a
TestSqlite* pair is added once persistence/sqlite/ exists.
"""

import pytest

from kungfu_chess.persistence.repositories import DuplicateUsernameError
from kungfu_chess.persistence.in_memory_repositories import (
    InMemoryUserRepository,
    InMemorySessionRepository,
)
from kungfu_chess.persistence.sqlite.sqlite_repositories import (
    SqliteUserRepository,
    SqliteSessionRepository,
    connect,
)


class UserRepositoryContract:
    @pytest.fixture
    def repository(self):
        raise NotImplementedError

    def test_add_then_get_by_username_returns_the_same_user(self, repository):
        user = repository.add("alice", "hash", "salt", 1200)
        assert repository.get_by_username("alice") == user

    def test_add_then_get_by_id_returns_the_same_user(self, repository):
        user = repository.add("alice", "hash", "salt", 1200)
        assert repository.get_by_id(user.user_id) == user

    def test_get_by_username_returns_none_for_unknown_username(self, repository):
        assert repository.get_by_username("nobody") is None

    def test_get_by_id_returns_none_for_unknown_id(self, repository):
        assert repository.get_by_id(999) is None

    def test_add_with_a_taken_username_raises(self, repository):
        repository.add("alice", "hash1", "salt1", 1200)
        with pytest.raises(DuplicateUsernameError):
            repository.add("alice", "hash2", "salt2", 1200)

    def test_update_rating_changes_the_stored_rating(self, repository):
        user = repository.add("alice", "hash", "salt", 1200)
        repository.update_rating(user.user_id, 1350)
        assert repository.get_by_id(user.user_id).rating == 1350
        assert repository.get_by_username("alice").rating == 1350


class SessionRepositoryContract:
    @pytest.fixture
    def repository(self):
        raise NotImplementedError

    def test_create_then_get_by_token_returns_the_same_session(self, repository):
        session = repository.create("tok1", 7)
        assert repository.get_by_token("tok1") == session
        assert session.user_id == 7

    def test_get_by_token_returns_none_for_unknown_token(self, repository):
        assert repository.get_by_token("nope") is None

    def test_delete_removes_the_session(self, repository):
        repository.create("tok1", 7)
        repository.delete("tok1")
        assert repository.get_by_token("tok1") is None

    def test_delete_is_a_no_op_for_an_unknown_token(self, repository):
        repository.delete("never-existed")


class TestInMemoryUserRepository(UserRepositoryContract):
    @pytest.fixture
    def repository(self):
        return InMemoryUserRepository()


class TestInMemorySessionRepository(SessionRepositoryContract):
    @pytest.fixture
    def repository(self):
        return InMemorySessionRepository()


class TestSqliteUserRepository(UserRepositoryContract):
    @pytest.fixture
    def repository(self):
        return SqliteUserRepository(connect(":memory:"))


class TestSqliteSessionRepository(SessionRepositoryContract):
    @pytest.fixture
    def repository(self):
        return SqliteSessionRepository(connect(":memory:"))
