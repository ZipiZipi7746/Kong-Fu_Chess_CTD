import pytest

from kungfu_chess.server.cli_login_flow import CliLoginFlow, LoginState


class TestCliLoginFlow:
    def test_starts_awaiting_username(self):
        flow = CliLoginFlow()
        assert flow.state == LoginState.AWAITING_USERNAME

    def test_submitting_username_advances_to_awaiting_password(self):
        flow = CliLoginFlow()
        flow.submit_username("alice")
        assert flow.state == LoginState.AWAITING_PASSWORD
        assert flow.username == "alice"

    def test_submitting_password_returns_the_username_and_password(self):
        flow = CliLoginFlow()
        flow.submit_username("alice")
        credentials = flow.submit_password("secret")
        assert credentials == ("alice", "secret")

    def test_submitting_password_before_username_raises(self):
        flow = CliLoginFlow()
        with pytest.raises(ValueError):
            flow.submit_password("secret")

    def test_submitting_username_twice_raises(self):
        flow = CliLoginFlow()
        flow.submit_username("alice")
        with pytest.raises(ValueError):
            flow.submit_username("alice-again")

    def test_mark_authenticated_advances_to_authenticated_and_stores_the_token(self):
        flow = CliLoginFlow()
        flow.submit_username("alice")
        flow.submit_password("secret")
        flow.mark_authenticated("session-token-123")
        assert flow.state == LoginState.AUTHENTICATED
        assert flow.session_token == "session-token-123"
