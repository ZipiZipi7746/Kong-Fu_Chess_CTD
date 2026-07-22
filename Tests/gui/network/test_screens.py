from kungfu_chess.gui.network.screens import LoginScreen, MenuScreen, WaitingScreen

CONTENT_W, CONTENT_H = 800, 600


class TestLoginScreen:
    def test_starts_with_the_username_field_focused(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        assert screen.username_field.focused is True
        assert screen.password_field.focused is False

    def test_clicking_the_password_field_focuses_it_instead(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        x, y = screen.password_hitbox.x + 1, screen.password_hitbox.y + 1
        screen.handle_click(x, y)
        assert screen.password_field.focused is True
        assert screen.username_field.focused is False

    def test_typed_characters_go_to_the_focused_field(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        screen.handle_char("a")
        screen.handle_char("b")
        assert screen.username_field.text == "ab"
        assert screen.password_field.text == ""

    def test_switching_focus_then_typing_goes_to_the_new_field(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        x, y = screen.password_hitbox.x + 1, screen.password_hitbox.y + 1
        screen.handle_click(x, y)
        screen.handle_char("s")
        assert screen.password_field.text == "s"
        assert screen.username_field.text == ""

    def test_backspace_affects_only_the_focused_field(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        screen.handle_char("a")
        screen.handle_backspace()
        assert screen.username_field.text == ""

    def test_tab_toggles_focus_between_the_two_fields(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        screen.handle_tab()
        assert screen.username_field.focused is False
        assert screen.password_field.focused is True
        screen.handle_tab()
        assert screen.username_field.focused is True
        assert screen.password_field.focused is False

    def test_clicking_the_new_account_toggle_flips_it(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        assert screen.is_new_account is False
        x, y = screen.new_account_toggle.x + 1, screen.new_account_toggle.y + 1
        screen.handle_click(x, y)
        assert screen.is_new_account is True
        screen.handle_click(x, y)
        assert screen.is_new_account is False

    def test_clicking_submit_returns_submit_action(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        x, y = screen.submit_button.x + 1, screen.submit_button.y + 1
        action = screen.handle_click(x, y)
        assert action == "submit"

    def test_clicking_empty_space_returns_no_action(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        action = screen.handle_click(0, 0)
        assert action is None

    def test_starts_with_no_error_message(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        assert screen.error_message is None


class TestMenuScreen:
    def test_clicking_quick_local_returns_that_action(self):
        screen = MenuScreen(CONTENT_W, CONTENT_H)
        x, y = screen.quick_local_button.x + 1, screen.quick_local_button.y + 1
        assert screen.handle_click(x, y) == "quick_local"

    def test_clicking_ranked_play_returns_that_action(self):
        screen = MenuScreen(CONTENT_W, CONTENT_H)
        x, y = screen.ranked_play_button.x + 1, screen.ranked_play_button.y + 1
        assert screen.handle_click(x, y) == "ranked_play"

    def test_clicking_create_room_returns_that_action(self):
        screen = MenuScreen(CONTENT_W, CONTENT_H)
        x, y = screen.create_room_button.x + 1, screen.create_room_button.y + 1
        assert screen.handle_click(x, y) == "create_room"

    def test_join_room_button_reveals_the_room_code_field(self):
        screen = MenuScreen(CONTENT_W, CONTENT_H)
        assert screen.showing_join_field is False
        x, y = screen.join_room_button.x + 1, screen.join_room_button.y + 1
        action = screen.handle_click(x, y)
        assert action is None
        assert screen.showing_join_field is True
        assert screen.room_code_field.focused is True

    def test_submitting_the_room_code_returns_join_room_action(self):
        screen = MenuScreen(CONTENT_W, CONTENT_H)
        x, y = screen.join_room_button.x + 1, screen.join_room_button.y + 1
        screen.handle_click(x, y)  # reveal the field
        screen.handle_char("a")
        screen.handle_char("b")
        x, y = screen.join_submit_button.x + 1, screen.join_submit_button.y + 1
        action = screen.handle_click(x, y)
        assert action == "join_room"
        assert screen.room_code_field.text == "ab"

    def test_typing_before_join_room_is_selected_does_nothing(self):
        screen = MenuScreen(CONTENT_W, CONTENT_H)
        screen.handle_char("a")
        assert screen.room_code_field.text == ""


class TestWaitingScreen:
    def test_stores_the_given_status_text(self):
        screen = WaitingScreen(CONTENT_W, CONTENT_H, "Waiting for an opponent...")
        assert screen.status_text == "Waiting for an opponent..."

    def test_clicking_cancel_returns_cancel_action(self):
        screen = WaitingScreen(CONTENT_W, CONTENT_H, "Searching for a ranked match...")
        x, y = screen.cancel_button.x + 1, screen.cancel_button.y + 1
        assert screen.handle_click(x, y) == "cancel"

    def test_clicking_elsewhere_returns_no_action(self):
        screen = WaitingScreen(CONTENT_W, CONTENT_H, "Waiting for an opponent...")
        assert screen.handle_click(0, 0) is None
