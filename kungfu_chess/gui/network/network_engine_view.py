"""Phase F Milestone 1: a read-only GameEngine-shaped adapter over the
latest render_state payload received from the server. Lets the existing
ViewModelRegistry/cooldown-highlight drawing code (built against a real
local GameEngine) consume network state through the exact same method
surface, without either of them needing to know the difference.

Holds no board-legality logic and imports nothing from
kungfu_chess.rules/realtime/model - it only ever remembers whatever the
server's most recent render_state said (Master Plan v2 Section 1's hard
rule: the client only ever renders and requests).

The server only broadcasts a fresh render_state every ~75ms
(server_main.py's TICK_INTERVAL_MS), but the render loop draws far more
often - advance(dt_ms) accumulates real per-frame time since the last
update() so motion_progress() can extrapolate smoothly between server
ticks using the progress rate observed across the last two updates,
rather than holding a motion frozen for ~75ms then jumping. This is pure
polish: the server's own progress value is still authoritative, and
extrapolation is capped short of full arrival so a motion is never shown
as complete before the server itself says so (has_pending_move_from is
unaffected)."""

_MAX_EXTRAPOLATED_PROGRESS = 0.99


class NetworkEngineView:
    def __init__(self):
        self.game_over = False
        self.winner = None
        self._motions_by_cell = {}
        self._cooldowns_by_cell = {}
        self._airborne_cells = set()
        self._motion_rates_by_cell = {}
        self._ms_since_update = 0

    def advance(self, dt_ms):
        self._ms_since_update += dt_ms

    def update(self, render_state):
        """Accepts either a full render_state payload or a state_snapshot/
        game_started payload (board/sequence/game_over/winner only, no
        motions/cooldowns/airborne keys) - the network game loop feeds
        both shapes through this same call rather than branching on
        message type."""
        new_motions_by_cell = {
            (motion["from"][0], motion["from"][1]): motion
            for motion in render_state.get("motions", [])
        }
        self._motion_rates_by_cell = {}
        for cell, motion in new_motions_by_cell.items():
            previous = self._motions_by_cell.get(cell)
            if previous is not None and self._ms_since_update > 0:
                delta = motion["progress"] - previous["progress"]
                if delta > 0:
                    self._motion_rates_by_cell[cell] = delta / self._ms_since_update
        self._ms_since_update = 0

        self.game_over = render_state["game_over"]
        self.winner = render_state["winner"]
        self._motions_by_cell = new_motions_by_cell
        self._cooldowns_by_cell = {
            (cooldown["row"], cooldown["col"]): cooldown["progress"]
            for cooldown in render_state.get("cooldowns", [])
        }
        self._airborne_cells = {
            (cell["row"], cell["col"]) for cell in render_state.get("airborne", [])
        }

    def has_pending_move_from(self, row, col):
        return (row, col) in self._motions_by_cell

    def is_airborne(self, row, col):
        return (row, col) in self._airborne_cells

    def is_on_cooldown(self, row, col):
        return (row, col) in self._cooldowns_by_cell

    def cooldown_progress(self, row, col):
        return self._cooldowns_by_cell.get((row, col))

    def motion_progress(self, row, col):
        motion = self._motions_by_cell.get((row, col))
        if motion is None:
            return None
        rate = self._motion_rates_by_cell.get((row, col))
        if rate is None:
            return motion["progress"]
        extrapolated = motion["progress"] + rate * self._ms_since_update
        return min(extrapolated, _MAX_EXTRAPOLATED_PROGRESS)

    def motion_target(self, row, col):
        motion = self._motions_by_cell.get((row, col))
        return tuple(motion["to"]) if motion is not None else None
