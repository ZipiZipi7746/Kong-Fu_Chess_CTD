import json
from pathlib import Path


def sprite_path(pieces_root, piece_code, state, frame_index):
    """Pure: which file to request for a given piece/state/frame - no
    disk access, no knowledge of how many frames exist."""
    return Path(pieces_root) / piece_code / "states" / state / "sprites" / f"{frame_index}.png"


class SpriteLibrary:
    """Strategy, chosen via DI: pieces_root is a constructor argument, so
    swapping sprite sets (pieces_mine / pieces1 / pieces2 / a future set)
    is a one-value change, never a code branch."""

    def __init__(self, pieces_root):
        self.pieces_root = Path(pieces_root)

    def load(self, piece_code, state):
        state_dir = self.pieces_root / piece_code / "states" / state
        with open(state_dir / "config.json", encoding="utf-8") as f:
            config = json.load(f)

        sprites_dir = state_dir / "sprites"
        frame_count = len(list(sprites_dir.glob("*.png")))
        frames = [
            sprite_path(self.pieces_root, piece_code, state, i)
            for i in range(1, frame_count + 1)
        ]
        return frames, config
