"""Pure draw-instruction layout for the graphical login/menu/waiting
screens - each function returns what to draw and where, never draws
anything itself (matching gui/hud/hud.py's own convention elsewhere in
this project). Returns a list of instructions, each either
("rect", x, y, w, h, color) or ("text", text, x, y, color) - the real
screen loop (screen_loop.py) is the only place that turns these into
actual ImgRenderer calls."""

# All colors are BGR (not RGB) - this project's cv2-based rendering
# pipeline uses OpenCV's native channel order throughout (see e.g.
# gui/game_loop.py's SELECTED_COLOR), confirmed by a rendering bug this
# module's FIELD_FOCUSED_COLOR originally had: written as if RGB, it
# rendered reddish instead of the intended blue.
FIELD_BG_COLOR = (60, 60, 60, 255)
FIELD_FOCUSED_COLOR = (150, 90, 90, 255)
BUTTON_COLOR = (70, 130, 70, 255)
TEXT_COLOR = (255, 255, 255, 255)
LABEL_COLOR = (200, 200, 200, 255)
ERROR_COLOR = (80, 80, 220, 255)


def _field_instructions(field, hitbox, label):
    color = FIELD_FOCUSED_COLOR if field.focused else FIELD_BG_COLOR
    return [
        ("rect", hitbox.x, hitbox.y, hitbox.width, hitbox.height, color),
        ("text", label, hitbox.x, hitbox.y - 8, LABEL_COLOR),
        ("text", field.display_text(), hitbox.x + 10, hitbox.y + hitbox.height // 2 + 5, TEXT_COLOR),
    ]


def _button_instructions(button):
    return [
        ("rect", button.x, button.y, button.width, button.height, BUTTON_COLOR),
        ("text", button.label, button.x + 10, button.y + button.height // 2 + 5, TEXT_COLOR),
    ]


def render_login_screen(screen):
    instructions = []
    instructions += _field_instructions(screen.username_field, screen.username_hitbox, "Username")
    instructions += _field_instructions(screen.password_field, screen.password_hitbox, "Password")
    toggle_label = "[x] New account?" if screen.is_new_account else "[ ] New account?"
    instructions.append((
        "text", toggle_label, screen.new_account_toggle.x, screen.new_account_toggle.y + 20, TEXT_COLOR))
    instructions += _button_instructions(screen.submit_button)
    if screen.error_message:
        instructions.append((
            "text", screen.error_message, screen.submit_button.x, screen.submit_button.y + 90, ERROR_COLOR))
    return instructions


def render_menu_screen(screen, username, rating):
    instructions = [
        ("text", f"{username}  (Rating: {rating})", screen.quick_local_button.x, 150, TEXT_COLOR),
    ]
    instructions += _button_instructions(screen.quick_local_button)
    instructions += _button_instructions(screen.ranked_play_button)
    instructions += _button_instructions(screen.create_room_button)
    instructions += _button_instructions(screen.join_room_button)
    if screen.showing_join_field:
        instructions += _field_instructions(screen.room_code_field, screen.room_code_hitbox, "Room code")
        instructions += _button_instructions(screen.join_submit_button)
    return instructions


def render_waiting_screen(screen):
    instructions = [("text", screen.status_text, screen.cancel_button.x, 250, TEXT_COLOR)]
    instructions += _button_instructions(screen.cancel_button)
    return instructions
