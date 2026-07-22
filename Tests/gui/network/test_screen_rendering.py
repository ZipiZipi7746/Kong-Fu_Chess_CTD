from kungfu_chess.gui.network.screens import LoginScreen, MenuScreen, WaitingScreen
from kungfu_chess.gui.network import screen_rendering as render

CONTENT_W, CONTENT_H = 800, 600


def _texts(instructions):
    return [args[0] for kind, *args in instructions if kind == "text"]


def _rects(instructions):
    return [args for kind, *args in instructions if kind == "rect"]


class TestRenderLoginScreen:
    def test_includes_the_typed_username_and_masked_password(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        screen.handle_char("a")
        screen.handle_tab()
        screen.handle_char("s")
        instructions = render.render_login_screen(screen)
        assert "a" in _texts(instructions)
        assert "*" in _texts(instructions)
        assert "s" not in _texts(instructions)  # never the raw password text

    def test_includes_a_submit_button_label(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        instructions = render.render_login_screen(screen)
        assert "Submit" in _texts(instructions)

    def test_focused_field_gets_a_different_rect_color_than_unfocused(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        instructions = render.render_login_screen(screen)
        rects = _rects(instructions)
        username_rect = next(r for r in rects if (r[0], r[1]) == (screen.username_hitbox.x, screen.username_hitbox.y))
        password_rect = next(r for r in rects if (r[0], r[1]) == (screen.password_hitbox.x, screen.password_hitbox.y))
        assert username_rect[-1] != password_rect[-1]

    def test_new_account_toggle_label_reflects_its_state(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        assert not any("[x]" in t for t in _texts(render.render_login_screen(screen)))
        screen.is_new_account = True
        assert any("[x]" in t for t in _texts(render.render_login_screen(screen)))

    def test_error_message_is_shown_when_set(self):
        screen = LoginScreen(CONTENT_W, CONTENT_H)
        assert "Login failed: INVALID_CREDENTIALS" not in _texts(render.render_login_screen(screen))
        screen.error_message = "Login failed: INVALID_CREDENTIALS"
        assert "Login failed: INVALID_CREDENTIALS" in _texts(render.render_login_screen(screen))


class TestRenderMenuScreen:
    def test_shows_username_and_rating(self):
        screen = MenuScreen(CONTENT_W, CONTENT_H)
        instructions = render.render_menu_screen(screen, "alice", 1200)
        joined = " ".join(_texts(instructions))
        assert "alice" in joined
        assert "1200" in joined

    def test_all_four_buttons_are_present(self):
        screen = MenuScreen(CONTENT_W, CONTENT_H)
        texts = _texts(render.render_menu_screen(screen, "alice", 1200))
        assert "Quick Local" in texts
        assert "Ranked Play" in texts
        assert "Create Room" in texts
        assert "Join Room" in texts

    def test_room_code_field_hidden_until_join_room_is_clicked(self):
        screen = MenuScreen(CONTENT_W, CONTENT_H)
        texts_before = _texts(render.render_menu_screen(screen, "alice", 1200))
        assert "Join" not in texts_before  # the submit button, not "Join Room"

        screen.handle_click(screen.join_room_button.x + 1, screen.join_room_button.y + 1)
        texts_after = _texts(render.render_menu_screen(screen, "alice", 1200))
        assert "Join" in texts_after


class TestRenderWaitingScreen:
    def test_shows_the_status_text(self):
        screen = WaitingScreen(CONTENT_W, CONTENT_H, "Waiting for an opponent...")
        texts = _texts(render.render_waiting_screen(screen))
        assert "Waiting for an opponent..." in texts

    def test_shows_a_cancel_button(self):
        screen = WaitingScreen(CONTENT_W, CONTENT_H, "Searching...")
        texts = _texts(render.render_waiting_screen(screen))
        assert "Cancel" in texts
