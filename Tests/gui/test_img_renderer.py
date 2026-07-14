import cv2
import numpy as np

from kungfu_chess.gui.img_adapter import Img
from kungfu_chess.gui.img_renderer import ImgRenderer


def make_solid_png(path, width, height, bgr_color):
    img = np.zeros((height, width, 4), dtype=np.uint8)
    img[:, :, 0] = bgr_color[0]
    img[:, :, 1] = bgr_color[1]
    img[:, :, 2] = bgr_color[2]
    img[:, :, 3] = 255  # fully opaque
    cv2.imwrite(str(path), img)


class TestImgRendererDrawSprite:
    def test_sprite_is_centered_within_the_target_box(self, tmp_path):
        # A narrow, tall sprite (20x40) drawn into a 40x40 box: keep_aspect
        # scales it to fit without distortion, leaving a transparent
        # margin on the sides that draw_sprite must center, not left-align.
        sprite_path = tmp_path / "sprite.png"
        make_solid_png(sprite_path, width=20, height=40, bgr_color=(0, 0, 255))  # red

        canvas = Img()
        canvas.img = np.zeros((60, 60, 4), dtype=np.uint8)  # transparent canvas
        renderer = ImgRenderer(canvas)

        renderer.draw_sprite(str(sprite_path), x=10, y=5, size=(40, 40))

        # Center of the sprite (offset_x=10+10=20 .. 40, offset_y=5..45)
        center_pixel = canvas.img[25, 30]
        assert tuple(center_pixel[:3]) == (0, 0, 255)

        # Left margin of the target box should NOT have been painted -
        # proves it was centered, not left-aligned.
        left_margin_pixel = canvas.img[25, 12]
        assert tuple(left_margin_pixel) == (0, 0, 0, 0)

    def test_square_sprite_fills_square_box_with_no_margin(self, tmp_path):
        sprite_path = tmp_path / "sprite.png"
        make_solid_png(sprite_path, width=30, height=30, bgr_color=(255, 0, 0))  # blue

        canvas = Img()
        canvas.img = np.zeros((50, 50, 4), dtype=np.uint8)
        renderer = ImgRenderer(canvas)

        renderer.draw_sprite(str(sprite_path), x=0, y=0, size=(30, 30))

        assert tuple(canvas.img[0, 0][:3]) == (255, 0, 0)
        assert tuple(canvas.img[29, 29][:3]) == (255, 0, 0)
