"""Client-side CLI login flow (Master Plan v2, Decision 2 / Section 8's
Player Session State Machine) - the state machine every client (today:
reference_client.py; later, the Phase F GUI network client) drives
before sending any game command. Holds no networking of its own - a
caller supplies how username/password are actually collected and how
register/login envelopes are actually sent; this class only enforces
the sequence username -> password -> authenticated."""

import enum


class LoginState(enum.Enum):
    AWAITING_USERNAME = "awaiting_username"
    AWAITING_PASSWORD = "awaiting_password"
    AUTHENTICATED = "authenticated"


class CliLoginFlow:
    def __init__(self):
        self.state = LoginState.AWAITING_USERNAME
        self.username = None
        self.password = None
        self.session_token = None

    def submit_username(self, username):
        if self.state != LoginState.AWAITING_USERNAME:
            raise ValueError(f"cannot submit username in state {self.state}")
        self.username = username
        self.state = LoginState.AWAITING_PASSWORD

    def submit_password(self, password):
        if self.state != LoginState.AWAITING_PASSWORD:
            raise ValueError(f"cannot submit password in state {self.state}")
        self.password = password
        return self.username, self.password

    def mark_authenticated(self, session_token):
        self.session_token = session_token
        self.state = LoginState.AUTHENTICATED
