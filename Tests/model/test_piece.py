from kungfu_chess.model.piece import Piece


class TestParse:
    def test_parse_empty_token_returns_none(self):
        assert Piece.parse(".") is None

    def test_parse_valid_token_returns_piece(self):
        piece = Piece.parse("wP")
        assert piece.color == "w"
        assert piece.kind == "P"

    # TODO(test): If parse()/__str__ are extracted into an injectable
    # PieceCodec (see the TODO on Piece), a round-trip contract test -
    # codec.decode(codec.encode(piece)) == piece for every (color, kind)
    # combination, run against each codec implementation - would replace
    # today's parse/str-specific tests and guarantee any future codec
    # (e.g. binary) honors the same contract as the text one.


class TestIsSameColor:
    def test_same_color_returns_true(self):
        white_a = Piece("w", "P")
        white_b = Piece("w", "R")
        assert white_a.is_same_color(white_b) is True

    def test_different_color_returns_false(self):
        white = Piece("w", "P")
        black = Piece("b", "P")
        assert white.is_same_color(black) is False

    def test_none_other_returns_false(self):
        white = Piece("w", "P")
        assert white.is_same_color(None) is False


class TestIsKing:
    def test_king_returns_true(self):
        assert Piece("w", "K").is_king() is True

    def test_non_king_returns_false(self):
        assert Piece("w", "Q").is_king() is False


class TestIsPawn:
    def test_pawn_returns_true(self):
        assert Piece("b", "P").is_pawn() is True

    def test_non_pawn_returns_false(self):
        assert Piece("b", "R").is_pawn() is False


class TestStr:
    def test_str_concatenates_color_and_kind(self):
        assert str(Piece("w", "N")) == "wN"
        assert str(Piece("b", "Q")) == "bQ"
