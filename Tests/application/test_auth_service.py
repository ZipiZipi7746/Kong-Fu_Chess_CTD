import pytest

from kungfu_chess.application.auth_service import (
    AuthenticationService,
    InvalidCredentialsError,
    create_sqlite_backed_service,
)
from kungfu_chess.persistence.repositories import DuplicateUsernameError
from kungfu_chess.persistence.in_memory_repositories import (
    InMemoryUserRepository,
    InMemorySessionRepository,
)

# A low iteration count keeps this suite fast - AuthenticationService's own
# default (Decision 3's real PBKDF2 cost) is exercised separately by
# test_uses_the_configured_iteration_count_by_default below.
_FAST_ITERATIONS = 10


def make_service(iterations=_FAST_ITERATIONS):
    return AuthenticationService(
        InMemoryUserRepository(), InMemorySessionRepository(),
        pbkdf2_iterations=iterations)


class TestRegister:
    def test_register_creates_a_user_with_the_default_rating(self):
        service = make_service()
        user = service.register("alice", "correct horse battery staple")
        assert user.username == "alice"
        assert user.rating == 1200

    def test_register_never_stores_the_plaintext_password(self):
        service = make_service()
        user = service.register("alice", "hunter2")
        assert "hunter2" not in user.password_hash
        assert user.password_hash != "hunter2"

    def test_two_users_registering_the_same_password_get_different_hashes(self):
        # Per-user salt (Decision 3) - equal passwords must not produce
        # equal hashes, or a leaked hash table would reveal shared passwords.
        service = make_service()
        alice = service.register("alice", "same-password")
        bob = service.register("bob", "same-password")
        assert alice.password_hash != bob.password_hash

    def test_registering_a_taken_username_raises(self):
        service = make_service()
        service.register("alice", "pw1")
        with pytest.raises(DuplicateUsernameError):
            service.register("alice", "pw2")


class TestLogin:
    def test_login_with_correct_credentials_returns_a_session_token(self):
        service = make_service()
        service.register("alice", "correct-password")
        token = service.login("alice", "correct-password")
        assert isinstance(token, str)
        assert token != ""

    def test_login_with_wrong_password_raises(self):
        service = make_service()
        service.register("alice", "correct-password")
        with pytest.raises(InvalidCredentialsError):
            service.login("alice", "wrong-password")

    def test_login_with_unknown_username_raises(self):
        service = make_service()
        with pytest.raises(InvalidCredentialsError):
            service.login("nobody", "whatever")

    def test_each_login_issues_a_distinct_token(self):
        service = make_service()
        service.register("alice", "correct-password")
        token1 = service.login("alice", "correct-password")
        token2 = service.login("alice", "correct-password")
        assert token1 != token2


class TestResolveToken:
    def test_resolve_token_returns_the_logged_in_user(self):
        service = make_service()
        service.register("alice", "correct-password")
        token = service.login("alice", "correct-password")
        resolved = service.resolve_token(token)
        assert resolved.username == "alice"

    def test_resolve_token_returns_none_for_an_unknown_token(self):
        service = make_service()
        assert service.resolve_token("not-a-real-token") is None


class TestDefaultConfiguration:
    def test_uses_the_configured_iteration_count_by_default(self):
        service = AuthenticationService(InMemoryUserRepository(), InMemorySessionRepository())
        assert service._pbkdf2_iterations >= 100_000

    def test_defaults_to_real_in_memory_repositories_when_none_are_given(self):
        # Matches the project's established param=None -> real default DI
        # convention (GameEngine, GameSession) - no repository is required
        # to construct a usable service.
        service = AuthenticationService()
        user = service.register("alice", "correct-password")
        assert service.resolve_token(service.login("alice", "correct-password")).user_id == user.user_id


class TestCreateSqliteBackedService:
    def test_register_login_and_resolve_work_against_a_real_sqlite_connection(self):
        # server_main.py's composition root calls this instead of
        # importing persistence.sqlite directly (Master Plan v2 Section 5
        # forbids server/ from importing persistence.sqlite except
        # through an application/*_service.py).
        service = create_sqlite_backed_service(":memory:", pbkdf2_iterations=_FAST_ITERATIONS)
        user = service.register("alice", "correct-password")
        token = service.login("alice", "correct-password")
        assert service.resolve_token(token).user_id == user.user_id

    def test_accounts_persist_across_services_sharing_the_same_db_file(self, tmp_path):
        db_path = str(tmp_path / "kungfu_chess_test.db")
        first_service = create_sqlite_backed_service(db_path, pbkdf2_iterations=_FAST_ITERATIONS)
        first_service.register("alice", "correct-password")

        second_service = create_sqlite_backed_service(db_path, pbkdf2_iterations=_FAST_ITERATIONS)
        token = second_service.login("alice", "correct-password")
        assert second_service.resolve_token(token).username == "alice"
