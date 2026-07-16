import json

from kungfu_chess.gui.animation.sprite_library import SpriteLibrary, sprite_path


class TestSpritePath:
    def test_builds_path_from_parts(self):
        path = sprite_path("assets/pieces_mine", "wK", "idle", 1)
        assert str(path).replace("\\", "/") == "assets/pieces_mine/wK/states/idle/sprites/1.png"

    def test_different_frame_index(self):
        path = sprite_path("assets/pieces_mine", "bN", "move", 3)
        assert str(path).replace("\\", "/") == "assets/pieces_mine/bN/states/move/sprites/3.png"


def make_fake_piece(root, code, state, frame_count, config):
    state_dir = root / code / "states" / state
    sprites_dir = state_dir / "sprites"
    sprites_dir.mkdir(parents=True)
    (state_dir / "config.json").write_text(json.dumps(config))
    for i in range(1, frame_count + 1):
        (sprites_dir / f"{i}.png").write_bytes(b"")


class TestSpriteLibraryLoad:
    def test_returns_all_frame_paths_in_order(self, tmp_path):
        config = {"physics": {"speed_m_per_sec": 1.5, "next_state_when_finished": "long_rest"},
                  "graphics": {"frames_per_sec": 12, "is_loop": True}}
        make_fake_piece(tmp_path, "wK", "idle", 5, config)

        library = SpriteLibrary(tmp_path)
        frames, loaded_config = library.load("wK", "idle")

        assert [f.name for f in frames] == ["1.png", "2.png", "3.png", "4.png", "5.png"]
        assert loaded_config == config

    def test_different_states_are_independent(self, tmp_path):
        idle_config = {"graphics": {"is_loop": True}}
        jump_config = {"graphics": {"is_loop": False}}
        make_fake_piece(tmp_path, "bR", "idle", 5, idle_config)
        make_fake_piece(tmp_path, "bR", "jump", 3, jump_config)

        library = SpriteLibrary(tmp_path)
        idle_frames, idle_loaded = library.load("bR", "idle")
        jump_frames, jump_loaded = library.load("bR", "jump")

        assert len(idle_frames) == 5
        assert len(jump_frames) == 3
        assert idle_loaded["graphics"]["is_loop"] is True
        assert jump_loaded["graphics"]["is_loop"] is False

    def test_pieces_root_is_swappable_via_constructor(self, tmp_path):
        # Strategy pattern: a different pieces_root is just a different
        # constructor argument, not a code branch.
        set_a = tmp_path / "set_a"
        set_b = tmp_path / "set_b"
        make_fake_piece(set_a, "wP", "idle", 1, {})
        make_fake_piece(set_b, "wP", "idle", 2, {})

        assert len(SpriteLibrary(set_a).load("wP", "idle")[0]) == 1
        assert len(SpriteLibrary(set_b).load("wP", "idle")[0]) == 2
