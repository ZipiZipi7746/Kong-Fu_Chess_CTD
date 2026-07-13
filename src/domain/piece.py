from dataclasses import dataclass


@dataclass(frozen=True)
class Piece:
    """Pure data model for a single piece. Carries no rendering or
    movement-rule logic of its own (SRP)."""

    color: str  # "w" or "b"
    kind: str   # "K", "Q", "R", "B", "N", "P"

    @staticmethod
    def parse(token):
        if token == ".":
            return None
        return Piece(token[0], token[1])

    def is_same_color(self, other):
        return other is not None and other.color == self.color

    def is_king(self):
        return self.kind == "K"

    def is_pawn(self):
        return self.kind == "P"

    def __str__(self):
        return f"{self.color}{self.kind}"
