from kungfu_chess.server.connection_manager import ConnectionManager


class TestRegisterAndSocket:
    def test_registered_connections_socket_is_retrievable(self):
        manager = ConnectionManager()
        manager.register("c1", socket="fake-socket-object")
        assert manager.get_socket("c1") == "fake-socket-object"

    def test_unregistered_connection_socket_is_none(self):
        manager = ConnectionManager()
        assert manager.get_socket("unknown") is None

    def test_unregister_removes_the_connection(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s")
        manager.unregister("c1")
        assert manager.get_socket("c1") is None


class TestIdentity:
    def test_identity_defaults_to_none(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s")
        assert manager.get_identity("c1") is None

    def test_set_identity_is_retrievable(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s")
        manager.set_identity("c1", "alice")
        assert manager.get_identity("c1") == "alice"


class TestFindConnectionByIdentity:
    def test_finds_the_connection_with_the_given_identity(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s1")
        manager.register("c2", socket="s2")
        manager.set_identity("c1", "alice")
        manager.set_identity("c2", "bob")
        assert manager.find_connection_by_identity("bob") == "c2"

    def test_returns_none_for_an_unknown_identity(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s1")
        manager.set_identity("c1", "alice")
        assert manager.find_connection_by_identity("nobody") is None


class TestSessionToken:
    def test_session_token_defaults_to_none(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s")
        assert manager.get_session_token("c1") is None

    def test_set_session_token_is_retrievable(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s")
        manager.set_session_token("c1", "tok-123")
        assert manager.get_session_token("c1") == "tok-123"


class TestRoomAssignment:
    def test_room_id_defaults_to_none(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s")
        assert manager.get_room_id("c1") is None

    def test_set_room_id_is_retrievable(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s")
        manager.set_room_id("c1", "AB3XZ")
        assert manager.get_room_id("c1") == "AB3XZ"


class TestGameAssignment:
    def test_game_id_defaults_to_none(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s")
        assert manager.get_game_id("c1") is None

    def test_set_game_id_is_retrievable(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s")
        manager.set_game_id("c1", "g_1")
        assert manager.get_game_id("c1") == "g_1"

    def test_connections_in_game_returns_only_matching_connections(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s1")
        manager.register("c2", socket="s2")
        manager.register("c3", socket="s3")
        manager.set_game_id("c1", "g_1")
        manager.set_game_id("c2", "g_1")
        manager.set_game_id("c3", "g_2")

        assert set(manager.connections_in_game("g_1")) == {"c1", "c2"}

    def test_connections_in_game_excludes_unassigned_connections(self):
        manager = ConnectionManager()
        manager.register("c1", socket="s1")
        assert manager.connections_in_game("g_1") == []
