from dataclasses import dataclass


@dataclass(frozen=True)
class Piece:
    """Pure data model for a single piece. Carries no rendering or
    movement-rule logic of its own (SRP)."""

    # TODO(design): The valid kind letters ("K","Q","R","B","N","P") and
    # what they mean are currently re-declared independently in several
    # places: piece_rules.PIECE_RULES (movement), promotion_rule.py
    # (promotion target), io/board_validator.VALID_PIECES (token
    # validation), and gui/hud/observers.py (_PIECE_VALUES/_PIECE_NAMES
    # for scoring/display). A central PieceDefinition registry (one
    # record per kind: rule, display name, material value, promotable-to)
    # would give this project a Single Source of Truth and reduce how
    # many files change when a piece is added or tuned (Registry Pattern,
    # DRY, Open/Closed). Note this is a spectrum: a fixed Enum would add
    # type safety for this project's closed set of six kinds, but a
    # dynamic dict-based registry (like PIECE_RULES already is) is what
    # would be needed if user-defined/custom pieces are ever supported -
    # worth deciding deliberately rather than defaulting to Enum. Not
    # done now: the duplication today is small (5 files, one line each)
    # and a registry would be speculative until a second piece set/variant
    # actually exists.
    color: str  # "w" or "b"
    kind: str   # "K", "Q", "R", "B", "N", "P"

    # TODO(design): Text (de)serialization of a Piece ("wK" <-> Piece)
    # lives directly on the domain object via parse()/__str__(), and is
    # invoked from Board.__init__ and BoardRenderer.to_rows respectively.
    # Extracting an injectable PieceCodec (e.g. TextPieceCodec, with a
    # BinaryPieceCodec possible later) would separate the domain model
    # from any particular wire/storage format (Strategy/Adapter,
    # Dependency Inversion, SRP) and let a new format be added without
    # touching Piece, Board or BoardRenderer. Not extracted now: there is
    # exactly one format in use, and a codec seam would be speculative
    # until a second one is actually needed.
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
