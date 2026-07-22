"""Wire protocol message-type vocabulary - the single source of truth
for every message type name. WebSocketGateway._HANDLER_NAMES imports
these instead of re-typing the string literals, and so does every
client (reference_client.py, login_client.py, gui/network/*.py) when
constructing an envelope - server and client can no longer silently
drift on the spelling of a message type, since both sides import the
same constant.

Values themselves are unchanged from before this module existed (this
is a pure refactor - see Tests/server/test_websocket_gateway.py, which
still asserts on the literal wire strings, since that is what actually
crosses the network and is what those tests are exercising)."""

# Client -> server
REGISTER = "register"
LOGIN = "login"
RECONNECT = "reconnect"
JOIN_GAME = "join_game"
PLAY = "play"
CANCEL_MATCHMAKING = "cancel_matchmaking"
CREATE_ROOM = "create_room"
JOIN_ROOM = "join_room"
MOVE_REQUEST = "move_request"
JUMP_REQUEST = "jump_request"
PING = "ping"

# Server -> client
REGISTERED = "registered"
LOGIN_OK = "login_ok"
STATE_SNAPSHOT = "state_snapshot"
GAME_STARTED = "game_started"
GAME_EVENT = "game_event"
GAME_OVER = "game_over"
MOVE_ACCEPTED = "move_accepted"
MOVE_REJECTED = "move_rejected"
SEARCHING_MATCH = "searching_match"
MATCHMAKING_TIMEOUT = "matchmaking_timeout"
ROOM_CREATED = "room_created"
ROOM_JOINED = "room_joined"
PLAYER_DISCONNECTED = "player_disconnected"
RENDER_STATE = "render_state"
PONG = "pong"
ERROR = "error"
