from kungfu_chess.server import protocol


class TestProtocolConstants:
    def test_client_to_server_message_types_are_the_expected_strings(self):
        assert protocol.REGISTER == "register"
        assert protocol.LOGIN == "login"
        assert protocol.RECONNECT == "reconnect"
        assert protocol.JOIN_GAME == "join_game"
        assert protocol.PLAY == "play"
        assert protocol.CANCEL_MATCHMAKING == "cancel_matchmaking"
        assert protocol.CREATE_ROOM == "create_room"
        assert protocol.JOIN_ROOM == "join_room"
        assert protocol.MOVE_REQUEST == "move_request"
        assert protocol.JUMP_REQUEST == "jump_request"
        assert protocol.PING == "ping"

    def test_server_to_client_message_types_are_the_expected_strings(self):
        assert protocol.REGISTERED == "registered"
        assert protocol.LOGIN_OK == "login_ok"
        assert protocol.STATE_SNAPSHOT == "state_snapshot"
        assert protocol.GAME_STARTED == "game_started"
        assert protocol.GAME_EVENT == "game_event"
        assert protocol.GAME_OVER == "game_over"
        assert protocol.MOVE_ACCEPTED == "move_accepted"
        assert protocol.MOVE_REJECTED == "move_rejected"
        assert protocol.SEARCHING_MATCH == "searching_match"
        assert protocol.MATCHMAKING_TIMEOUT == "matchmaking_timeout"
        assert protocol.ROOM_CREATED == "room_created"
        assert protocol.ROOM_JOINED == "room_joined"
        assert protocol.PLAYER_DISCONNECTED == "player_disconnected"
        assert protocol.RENDER_STATE == "render_state"
        assert protocol.PONG == "pong"
        assert protocol.ERROR == "error"

    def test_no_two_constants_share_the_same_wire_value(self):
        # Every message type must be spelled exactly once - a silent
        # collision here would mean two different messages become
        # indistinguishable on the wire.
        values = [
            value for name, value in vars(protocol).items()
            if not name.startswith("_") and isinstance(value, str)
        ]
        assert len(values) == len(set(values))
