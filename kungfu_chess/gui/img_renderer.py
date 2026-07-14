from kungfu_chess.gui.img_adapter import Img
from kungfu_chess.gui.renderer import Renderer


class ImgRenderer(Renderer):
    """The only Renderer implementation that exists or is allowed (per
    the instructor's Img-only requirement): every draw call composites
    onto a single Img canvas solely via Img.draw_on."""

    def __init__(self, canvas: Img):
        self.canvas = canvas

    def draw_sprite(self, path, x, y, size):
        sprite = Img().read(path, size=size, keep_aspect=True)
        sprite_h, sprite_w = sprite.img.shape[:2]
        offset_x = x + (size[0] - sprite_w) // 2
        offset_y = y + (size[1] - sprite_h) // 2
        sprite.draw_on(self.canvas, offset_x, offset_y)
