import asyncio

from kungfu_chess.engine.events import EventBus
from kungfu_chess.engine.game_engine import GameEngine


class GameSession:
    """The authoritative aggregate for one running game (Part 9 of the
    architecture plan). Owns exactly what GameEngine does NOT and must
    never know about: the network-facing player identities, the per-game
    concurrency lock, and a monotonic sequence number for state
    broadcasts. GameEngine itself is constructed here unmodified, with
    this session's own EventBus injected exactly as gui/game_loop.py
    already does - GameSession adds nothing to GameEngine's constructor
    contract, it just owns the instance.

    white/black are Phase A display-name strings (see
    application.auth_service - identify() has no password/persistence
    yet); color_for() is how GameService authorizes a move/jump request
    against the color of the piece actually being moved, never against
    "whose turn it is" - this engine has no turn concept (RuleEngine's own
    docstring: "Still does NOT check turn order"), so enforcing turns at
    this layer would silently break the dodge mechanic both colors rely
    on to have independent motions in flight at once.
    """

    def __init__(self, game_id, board, white, black, jump_duration_ms=1000,
                 move_cooldown_ms=None, jump_cooldown_ms=None, rated=False):
        self.game_id = game_id
        self.white = white
        self.black = black
        self.event_bus = EventBus()
        self.engine = GameEngine(
            board, jump_duration_ms, event_bus=self.event_bus,
            move_cooldown_ms=move_cooldown_ms, jump_cooldown_ms=jump_cooldown_ms)
        self.lock = asyncio.Lock()
        self.sequence = 0
        # Master Plan v2 Section 10.2/Section 9: Play-originated games are
        # rated (Decision 14), quick_local games are not. rating_applied
        # guards exactly-once rating application on game end - see
        # GameService._apply_rating.
        self.rated = rated
        self.rating_applied = False

    def color_for(self, display_name):
        if display_name == self.white:
            return "w"
        if display_name == self.black:
            return "b"
        return None

    def next_sequence(self):
        self.sequence += 1
        return self.sequence

    def has_pending_activity(self):
        """True if any motion is in flight, any piece is airborne, or any
        cell is on cooldown - i.e. this session still needs periodic
        advance_time ticks even without a new client command (Part 10's
        hybrid time-advancement design)."""
        arbiter = self.engine.arbiter
        return bool(arbiter.pending_motions or arbiter.airborne or arbiter.cooldowns)
