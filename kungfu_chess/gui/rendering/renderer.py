from abc import ABC, abstractmethod


class Renderer(ABC):
    """Thin interface for DI/testing only (per the instructor's Img-only
    requirement, this is not a channel for swapping graphics libraries -
    ImgRenderer is the only implementation that exists or is allowed)."""

    # NOTE(design): This abstraction already delivers what it's meant to:
    # game_loop and ViewModelRegistry depend on this interface rather
    # than on ImgRenderer/cv2 directly, and Tests/gui already exercises
    # that seam with a FakeRenderer test double. No further "alternative
    # backend" TODO is added here deliberately - that would conflict with
    # the Img-only constraint above, and a headless/test renderer already
    # exists via this same interface.

    @abstractmethod
    def draw_sprite(self, path, x, y, size):
        ...

    @abstractmethod
    def draw_text(self, text, x, y):
        ...

    @abstractmethod
    def draw_highlight(self, x, y, size, color):
        ...
