import subprocess
import sys
import textwrap

from kungfu_chess.main import run


class TestRun:
    def test_full_pipeline_executes_commands(self, capsys):
        run([
            "Board:",
            "wR .",
            ". bK",
            "Commands:",
            "print board",
        ])
        assert capsys.readouterr().out == "wR .\n. bK\n"

    def test_unknown_command_line_is_skipped(self, capsys):
        run([
            "Board:",
            "wR",
            "Commands:",
            "dance 1 2",
            "print board",
        ])
        assert capsys.readouterr().out == "wR\n"

    def test_invalid_board_prints_error(self, capsys):
        run([
            "Board:",
            "wR wR",
            "wR",
            "Commands:",
        ])
        out = capsys.readouterr().out
        assert out.startswith("ERROR ")

    def test_click_wait_and_capture_flow_end_to_end(self, capsys):
        run([
            "Board:",
            "wR bK",
            "Commands:",
            "click 0 0",
            "click 100 0",
            "wait 1000",
            "print board",
        ])
        assert capsys.readouterr().out == ". wR\n"

    def test_friendly_collision_later_mover_stops_short_end_to_end(self, capsys):
        # wR at col 0 travels 3 cells to col 3 (arrives at 3000ms); wR at
        # col 4 travels 1 cell to the same destination (arrives at
        # 1000ms) and claims it first. The later mover must stop one
        # cell short instead of landing on its friendly-occupied target.
        run([
            "Board:",
            "wR . . . wR",
            "Commands:",
            "click 0 0",
            "click 300 0",
            "click 400 0",
            "click 300 0",
            "wait 3000",
            "print board",
        ])
        assert capsys.readouterr().out == ". . wR wR .\n"

    def test_threatened_piece_can_dodge_before_the_attacker_arrives(self, capsys):
        # wR at col 0 heads for bR at col 3 (3 cells, 3000ms). bR flees
        # straight down (1 cell, 1000ms) - well clear before wR arrives.
        run([
            "Board:",
            "wR . . bR",
            ". . . .",
            "Commands:",
            "click 0 0",
            "click 300 0",
            "click 300 0",
            "click 300 100",
            "wait 3000",
            "print board",
        ])
        assert capsys.readouterr().out == ". . . wR\n. . . bR\n"


class TestMainSubprocess:
    """main() itself (reading real stdin) is a one-line wrapper around
    run(); it is exercised end-to-end via a real subprocess with piped
    stdin (no monkeypatching), which also implicitly proves run() and
    main() are wired together correctly."""

    def test_main_reads_real_stdin(self):
        script = textwrap.dedent("""
            from main import main
            main()
        """)
        result = subprocess.run(
            [sys.executable, "-c", script],
            input="Board:\nwR .\nCommands:\nprint board\n",
            capture_output=True,
            text=True,
            cwd=__import__("os").path.dirname(__file__),
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout == "wR .\n"
