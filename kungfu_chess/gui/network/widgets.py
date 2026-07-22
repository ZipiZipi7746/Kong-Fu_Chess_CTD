"""Minimal, framework-free UI primitives for the graphical login/menu
screens (gui/network/screens.py) - pure logic only, no cv2/rendering
here, matching gui/hud/hud.py's own "pure layout, never draws itself"
convention. A TextField holds a text buffer and simple edit operations
(no cursor positioning/selection - append/backspace only, sufficient
for a username/password/room-code field); a Button is just a
hit-testable rectangle plus a label."""


class TextField:
    def __init__(self, label, masked=False):
        self.label = label
        self.masked = masked
        self.text = ""
        self.focused = False

    def handle_char(self, char):
        if char.isprintable():
            self.text += char

    def handle_backspace(self):
        self.text = self.text[:-1]

    def clear(self):
        self.text = ""

    def display_text(self):
        return "*" * len(self.text) if self.masked else self.text


class Button:
    def __init__(self, label, x, y, width, height):
        self.label = label
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def contains_point(self, px, py):
        return (self.x <= px < self.x + self.width
                and self.y <= py < self.y + self.height)
