"""Pure logic for each pre-game graphical screen (login, menu, waiting) -
click/keyboard handling and layout positions only, no cv2/rendering
here (gui/network/screen_rendering.py owns drawing, matching gui/hud/
hud.py's own "pure layout, never draws itself" convention elsewhere in
this project). Button doubles as a generic hit-testable rectangle here,
used both for real buttons and for a TextField's invisible click
region - the same rect that positions it for drawing also decides
whether a click landed on it, exactly how BoardMapper/cell_to_pixel
already share position math between hit-testing and rendering
elsewhere in this codebase.

Each handle_click returns a symbolic action string (or None) - the real
I/O screen loop (screen_loop.py) is the only place that turns an action
into an actual network request or a screen transition.
"""

from kungfu_chess.gui.network.widgets import Button, TextField

_FIELD_WIDTH = 300
_FIELD_HEIGHT = 40


class LoginScreen:
    def __init__(self, content_w, content_h):
        cx = content_w // 2 - _FIELD_WIDTH // 2

        self.username_field = TextField("Username")
        self.username_hitbox = Button("", cx, 200, _FIELD_WIDTH, _FIELD_HEIGHT)
        self.username_field.focused = True

        self.password_field = TextField("Password", masked=True)
        self.password_hitbox = Button("", cx, 260, _FIELD_WIDTH, _FIELD_HEIGHT)

        self.new_account_toggle = Button("New account?", cx, 320, _FIELD_WIDTH, 30)
        self.is_new_account = False

        self.submit_button = Button("Submit", cx, 370, _FIELD_WIDTH, 50)
        self.error_message = None

    def handle_click(self, x, y):
        if self.username_hitbox.contains_point(x, y):
            self.username_field.focused = True
            self.password_field.focused = False
            return None
        if self.password_hitbox.contains_point(x, y):
            self.password_field.focused = True
            self.username_field.focused = False
            return None
        if self.new_account_toggle.contains_point(x, y):
            self.is_new_account = not self.is_new_account
            return None
        if self.submit_button.contains_point(x, y):
            return "submit"
        return None

    def handle_char(self, char):
        self._focused_field().handle_char(char)

    def handle_backspace(self):
        self._focused_field().handle_backspace()

    def handle_tab(self):
        self.username_field.focused, self.password_field.focused = (
            self.password_field.focused, self.username_field.focused)

    def _focused_field(self):
        return self.username_field if self.username_field.focused else self.password_field


class MenuScreen:
    def __init__(self, content_w, content_h):
        cx = content_w // 2 - _FIELD_WIDTH // 2

        self.quick_local_button = Button("Quick Local", cx, 200, _FIELD_WIDTH, 50)
        self.ranked_play_button = Button("Ranked Play", cx, 260, _FIELD_WIDTH, 50)
        self.create_room_button = Button("Create Room", cx, 320, _FIELD_WIDTH, 50)
        self.join_room_button = Button("Join Room", cx, 380, _FIELD_WIDTH, 50)

        self.showing_join_field = False
        self.room_code_field = TextField("Room code")
        self.room_code_hitbox = Button("", cx, 440, _FIELD_WIDTH, _FIELD_HEIGHT)
        self.join_submit_button = Button("Join", cx, 490, _FIELD_WIDTH, 50)

    def handle_click(self, x, y):
        if self.quick_local_button.contains_point(x, y):
            return "quick_local"
        if self.ranked_play_button.contains_point(x, y):
            return "ranked_play"
        if self.create_room_button.contains_point(x, y):
            return "create_room"
        if self.join_room_button.contains_point(x, y):
            self.showing_join_field = True
            self.room_code_field.focused = True
            return None
        if self.showing_join_field and self.room_code_hitbox.contains_point(x, y):
            self.room_code_field.focused = True
            return None
        if self.showing_join_field and self.join_submit_button.contains_point(x, y):
            return "join_room"
        return None

    def handle_char(self, char):
        if self.showing_join_field:
            self.room_code_field.handle_char(char)

    def handle_backspace(self):
        if self.showing_join_field:
            self.room_code_field.handle_backspace()


class WaitingScreen:
    def __init__(self, content_w, content_h, status_text):
        cx = content_w // 2 - _FIELD_WIDTH // 2
        self.status_text = status_text
        self.cancel_button = Button("Cancel", cx, 300, _FIELD_WIDTH, 50)

    def handle_click(self, x, y):
        if self.cancel_button.contains_point(x, y):
            return "cancel"
        return None
