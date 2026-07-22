from kungfu_chess.gui.network.widgets import Button, TextField


class TestTextField:
    def test_starts_empty_and_unfocused(self):
        field = TextField("Username")
        assert field.text == ""
        assert field.focused is False

    def test_handle_char_appends_to_the_text(self):
        field = TextField("Username")
        field.handle_char("a")
        field.handle_char("b")
        assert field.text == "ab"

    def test_handle_backspace_removes_the_last_character(self):
        field = TextField("Username")
        field.handle_char("a")
        field.handle_char("b")
        field.handle_backspace()
        assert field.text == "a"

    def test_handle_backspace_on_empty_text_stays_empty(self):
        field = TextField("Username")
        field.handle_backspace()
        assert field.text == ""

    def test_clear_empties_the_text(self):
        field = TextField("Username")
        field.handle_char("a")
        field.clear()
        assert field.text == ""

    def test_display_text_shows_the_real_text_when_not_masked(self):
        field = TextField("Username", masked=False)
        field.handle_char("h")
        field.handle_char("i")
        assert field.display_text() == "hi"

    def test_display_text_masks_when_masked(self):
        field = TextField("Password", masked=True)
        field.handle_char("h")
        field.handle_char("i")
        assert field.display_text() == "**"

    def test_non_printable_characters_are_ignored(self):
        field = TextField("Username")
        field.handle_char("\x1b")  # ESC is not printable
        assert field.text == ""


class TestButton:
    def test_contains_point_inside_the_rect(self):
        button = Button("OK", x=10, y=20, width=100, height=40)
        assert button.contains_point(50, 30) is True

    def test_contains_point_outside_the_rect(self):
        button = Button("OK", x=10, y=20, width=100, height=40)
        assert button.contains_point(5, 30) is False
        assert button.contains_point(200, 30) is False
        assert button.contains_point(50, 10) is False
        assert button.contains_point(50, 100) is False

    def test_contains_point_on_the_edge_is_inside(self):
        button = Button("OK", x=10, y=20, width=100, height=40)
        assert button.contains_point(10, 20) is True

    def test_contains_point_just_past_the_far_edge_is_outside(self):
        button = Button("OK", x=10, y=20, width=100, height=40)
        assert button.contains_point(110, 60) is False
