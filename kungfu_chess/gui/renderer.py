from abc import ABC, abstractmethod


class Renderer(ABC):
    """Thin interface for DI/testing only (per the instructor's Img-only
    requirement, this is not a channel for swapping graphics libraries -
    ImgRenderer is the only implementation that exists or is allowed)."""

    @abstractmethod
    def draw_sprite(self, path, x, y, size):
        ...

    @abstractmethod
    def draw_text(self, text, x, y):
        ...
