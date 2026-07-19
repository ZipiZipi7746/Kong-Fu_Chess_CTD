from dataclasses import dataclass


@dataclass(frozen=True)
class Piece:
    """Pure data model for a single piece. Carries no rendering or
    movement-rule logic of its own (SRP)."""

    # TODO(design): The valid kind letters ("K","Q","R","B","N","P") and
    # what they mean are still re-declared independently in a few places:
    # piece_rules.PIECE_RULES (movement rule), promotion_rule.py
    # (default promotion target), and gui/hud/observers.py
    # (_PIECE_VALUES/_PIECE_NAMES for scoring/display) - one fewer than
    # before, now that io/board_validator.py's valid-token check is
    # injected from (and defaults to) this same PIECE_RULES rather than
    # keeping its own separate set. A central PieceDefinition registry -
    # one record per kind, roughly:
    #
    #   PieceDefinition(kind=..., rule=..., display_name=...,
    #                    score_value=..., rendering_key=...,
    #                    duration_policy=..., transformation_policy=...)
    #
    # - would finish the job: adding or tuning a piece becomes
    # registering one definition, not editing rule/promotion/HUD code
    # separately (Registry Pattern, Single Source of Truth, DRY,
    # Open/Closed). This is a spectrum, not a single choice: a fixed Enum
    # would add type safety for a closed, standard-chess set of six
    # kinds, while a dynamic dict-based registry (like PIECE_RULES
    # already is) is what a runtime-defined or plugin piece kind would
    # actually need - the project's stated extensibility requirement
    # (variant rule sets, non-standard pieces) points at the dynamic
    # registry as the direction to build toward, not the enum. Required
    # architectural direction, not speculative - but still deferred: it
    # touches five collaborators at once (this class, piece_rules.py,
    # promotion_rule.py, board_validator.py, observers.py) and deserves
    # its own dedicated, test-driven pass rather than a guess bundled
    # into unrelated work.
    color: str  # "w" or "b"
    kind: str   # "K", "Q", "R", "B", "N", "P"

    # TODO(design): Text (de)serialization of a Piece ("wK" <-> Piece)
    # lives directly on the domain object via parse()/__str__(), and is
    # invoked from Board.__init__ and BoardRenderer.to_rows respectively.
    # Extracting an injectable PieceCodec (e.g. TextPieceCodec, with a
    # BinaryPieceCodec possible later) would separate the domain model
    # from any particular wire/storage format (Strategy/Adapter,
    # Dependency Inversion, SRP) and let a new format be added without
    # touching Piece, Board or BoardRenderer. Useful only once a second
    # format is actually needed (e.g. a saved-game file, a network wire
    # format) - not required by the board-shape/piece-rule extensibility
    # goal itself, so it stays a feature-triggered TODO rather than a
    # required direction.
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
