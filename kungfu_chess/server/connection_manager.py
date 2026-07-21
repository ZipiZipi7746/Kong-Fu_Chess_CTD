class ConnectionManager:
    """Tracks connection_id <-> socket <-> identity <-> game_id (Part 3 of
    the architecture plan). Deliberately holds sockets as opaque values -
    it never reads or writes to them itself, so it stays trivially
    testable with a plain string/fake standing in for a real WebSocket
    connection object; only WebSocketGateway ever calls send() on what's
    stored here."""

    def __init__(self):
        self._connections = {}

    def register(self, connection_id, socket):
        self._connections[connection_id] = {
            "socket": socket, "identity": None, "game_id": None, "session_token": None}

    def unregister(self, connection_id):
        self._connections.pop(connection_id, None)

    def get_socket(self, connection_id):
        return self._get(connection_id, "socket")

    def set_identity(self, connection_id, identity):
        self._connections[connection_id]["identity"] = identity

    def get_identity(self, connection_id):
        return self._get(connection_id, "identity")

    def set_session_token(self, connection_id, session_token):
        self._connections[connection_id]["session_token"] = session_token

    def get_session_token(self, connection_id):
        return self._get(connection_id, "session_token")

    def set_game_id(self, connection_id, game_id):
        self._connections[connection_id]["game_id"] = game_id

    def get_game_id(self, connection_id):
        return self._get(connection_id, "game_id")

    def connections_in_game(self, game_id):
        return [
            connection_id for connection_id, info in self._connections.items()
            if info["game_id"] == game_id
        ]

    def _get(self, connection_id, field):
        info = self._connections.get(connection_id)
        return info[field] if info is not None else None
