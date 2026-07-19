# Kung Fu Chess — Multiplayer Server Architecture & Development Plan (Updated)

*Prepared after inspecting the actual repository (`kungfu_chess/` package, `Tests/`, `requirements.txt`, `docs/design-dilemmas.html`, commits `bbcf16c`/`8fe7434`) and after cross-checking the product specification against the slide deck "CTD 26 (Server).pptx" (7 slides: BUS, Single-process server ×4, Rooms/logging). Every class, method, and file path named below was verified against the current source, not assumed. Changes made in this revision versus the first draft are marked **[UPDATED]**.*

*Note: Part 17 ("Generated Claude Code Planning Prompt") is intentionally not included in this file — it is delivered as plain text in the chat response body instead, per request.*

---

## Part 1 — Executive Summary

**What should be built:** a single-process, authoritative WebSocket server that sits *outside* `kungfu_chess/model`, `kungfu_chess/rules`, `kungfu_chess/realtime`, and `kungfu_chess/engine`, and depends on `GameEngine` the same way `GameController` already does today — by calling its existing public methods (`request_move`, `request_jump`, `advance_time`, the read-only query methods) and reading `board`/`game_over`/`winner`. No new method needs to be added to `GameEngine` for Phase A's move/jump flow to work; the API the server needs already exists.

**[UPDATED] One small, additive engine-layer change is still required, independent of the server:** the current `EventBus` never publishes anything when a game ends — only `MoveResolvedEvent` is published, on every arrival, regardless of outcome. The product specification's "BUS" slide explicitly requires the pub/sub bus to drive *sound* and *game start/end animations*, which is impossible today because no event exists to represent "the game just ended." This plan adds a `GameOverEvent` (domain event, in `engine/events.py`, published by `GameEngine._resolve_motion` at the exact point `self.game_over` becomes `True`) — a two-line, fully-tested addition to the *existing* Observer mechanism the GUI already partially uses (`MovesLogObserver`/`ScoreObserver`), not new coupling to the server.

**Recommended architecture:** a layered structure — `server` (WebSocket gateway, connection manager, JSON schemas) → `application` (new services: `GameService`, `RoomService`, `MatchmakingService`, `AuthenticationService`, `RatingService`, `ConnectionService`) → `engine`/`rules`/`realtime`/`model` (untouched except the one additive event noted above) — plus two new side-packages, `persistence` (repository interfaces + in-memory and SQLite implementations) and `messaging` (a new *application-level* pub/sub bus, sitting beside — not replacing — the existing per-game `EventBus`).

**Major risks:** (1) the temptation to let the WebSocket handler call `Board`/`RuleEngine` directly instead of going through `GameEngine.request_move`, duplicating rule logic outside the engine; (2) two concurrent commands mutating the same `GameSession` without a per-game serialization mechanism; (3) applying an ELO/rating update twice for the same game; (4) the real-time nature of this engine (`Motion`, cooldowns, airborne pieces) needs time to advance even when no client sends a message — a naive "advance time only on incoming command" design will silently stall in-flight motions; (5) **[UPDATED]** forgetting the `GameOverEvent` gap and having sound/animation consumers poll `engine.game_over` instead of subscribing to the bus, which defeats the specification's pub/sub requirement.

**Recommended implementation order:** Phase A (single-process WS server, two local clients, username-only shell identification, in-memory `GameSession`, the `GameOverEvent` addition, no password/persistence yet) → Phase B (SQLite users + password hashing + ELO, shell-based login) → Phase C (matchmaking) → Phase D (disconnect/reconnect/state sync) → Phase E (rooms/spectators/logging on both server and client). This order matches the specification and the deck, and is also the order of increasing coupling risk.

**What must NOT change in the current engine:** `Piece`, `Board`, `BoardTopology`/`RectangularTopology`, `PieceRule`/`PIECE_RULES`/`RuleEngine`, `PromotionRule`, `WinCondition`/`CaptureKingWinCondition`, `Motion`, `RealTimeArbiter`, `GameEngine`'s move/jump/time API — none of these gain any awareness of sockets, JSON, users, passwords, SQLite, or rooms. The **only** sanctioned change anywhere near the engine is the additive `GameOverEvent` in `engine/events.py`, which is a pure domain-event completion, not a server dependency.

---

## Part 2 — Current Repository Assessment

*(Every claim below was verified by reading the actual file, not inferred from names.)*

### Classes that can be reused as-is (dependency of the server, unmodified)

| Class / module | File | Why it's reusable unmodified |
|---|---|---|
| `Piece` | `model/piece.py` | Immutable value object, no I/O, no coupling. |
| `Board`, `RectangularTopology` | `model/board.py`, `model/board_topology.py` | `Board(cells, topology=None)` already supports DI; server never needs to touch `_cells` directly (`get_cell`/`set_cell`/`iter_rows`). |
| `PieceRule` hierarchy, `PIECE_RULES` (now includes `PawnRule`) | `rules/piece_rules.py` | Pure Strategy objects, no engine/server awareness. `PawnRule.is_legal` overrides the Template Method directly; all six kinds are invoked uniformly via `rule.is_legal(...)`. |
| `RuleEngine` | `rules/rule_engine.py` | `RuleEngine(rule_registry=None)` — already DI-friendly (verified: constructor accepts an injectable registry, defaults to `PIECE_RULES`); `is_legal(piece, from_row, from_col, to_row, to_col, board)` is exactly the shape a server-side move validator needs; `requires_clear_path` is now a per-rule flag rather than a hardcoded set. |
| `PromotionRule` | `rules/promotion_rule.py` | `resolve(piece, to_row, board, promotion_kind=None)` — already configurable (`DEFAULT_PROMOTION_KIND = "Q"`), no change needed. |
| `WinCondition` / `CaptureKingWinCondition` | `rules/win_condition.py` | Already an injectable Strategy on `GameEngine` (`GameEngine(..., win_condition=None)`); `check(moving_piece, captured_piece, board) -> winner|None`. |
| `Motion` | `realtime/motion.py` | Pure data + virtual-time math, no real clock. |
| `RealTimeArbiter` | `realtime/real_time_arbiter.py` | Deterministic, driven only by `advance(ms)` — perfect for a server-controlled virtual clock; exposes `has_pending_move_from`/`is_airborne`/`is_on_cooldown` used by the tick decision in Part 10. |
| `GameEngine` | `engine/game_engine.py` | **This is the server's real API surface.** Verified current signature: `__init__(self, board, jump_duration_ms, rule_engine=None, arbiter=None, event_bus=None, move_cooldown_ms=None, jump_cooldown_ms=None, win_condition=None)`, plus `request_move(from_row, from_col, to_row, to_col)`, `request_jump(row, col)`, `advance_time(ms)`, read-only `has_pending_move_from`/`is_airborne`/`is_on_cooldown`/`cooldown_progress`/`motion_progress`/`motion_target`, and public fields `board`, `game_over`, `winner`. |
| `EventBus` / `MoveResolvedEvent` | `engine/events.py` | Reusable **as the per-game domain event bus**, exactly as already injected into `GameEngine(event_bus=...)` in `gui/game_loop.py`. `subscribe(callback)`/`publish(event)`, synchronous, in-process. |
| `BoardParser` / `BoardValidator` | `io/board_parser.py`, `io/board_validator.py` | Reusable for constructing the *initial* board layout for a `GameSession`; `BoardValidator.validate(rows, valid_piece_kinds=None)` already defaults to `PIECE_RULES.keys()` (single source of truth). |

### **[UPDATED] Verified gap: no domain event exists for game-over or game-start**

Read in full: `GameEngine._resolve_motion` calls `self.win_condition.check(piece, destination, self.board)`, and if a winner is returned, sets `self.game_over = True` / `self.winner = winner` as **plain fields** — no event object is constructed or published for this. Immediately after, `MoveResolvedEvent` is published unconditionally (win or no win) and carries no `game_over`/`winner` field. Consequence: **a bus subscriber cannot currently tell, from anything published on `EventBus`, that the game just ended.** This directly blocks the specification's "use the bus for … adding sound … game start/end animations" requirement. Recommended fix (small, additive, unit-testable exactly like `MoveResolvedEvent` already is): add `GameOverEvent(winner, timestamp_ms)` to `engine/events.py`, publish it from `GameEngine._resolve_motion` at the point `self.game_over` is set to `True`. "Game started" has no equivalent moment inside `GameEngine` at all — it is not a domain event, it belongs as an **application** event (`GameStartedEvent`) published by `GameSession`/`GameService` the instant a session is constructed (Part 5).

### Classes that should NOT be reused for the server, and why

| Class | File | Reason to bypass |
|---|---|---|
| `GameController` | `input/controller.py` | Verified: `click(x, y)` takes **pixel coordinates**, delegates to `BoardMapper.to_cell`, and owns a single mutable `self.selected` two-click state machine designed for **one local human clicking twice on one screen**. A server has two independent remote players who each send one fully-specified move; there is no click-selection ambiguity to resolve. `GameController` also constructs its own `GameEngine` internally if none is injected, and calls `BoardRenderer.render(board)` (prints to stdout). **Verdict: the server calls `GameEngine` directly, not `GameController`.** |
| `BoardMapper` | `input/board_mapper.py` | Pixel→grid conversion; irrelevant once the client sends structured `(from_row, from_col, to_row, to_col)` in JSON. |
| `BoardRenderer` | `io/board_view.py` | Produces a text grid for `print()`; the server needs a JSON-serializable board snapshot instead (a new, small DTO mapper). |
| `commands.py` (`ClickCommand`/`WaitCommand`/`JumpCommand`/`PrintBoardCommand`) | `input/commands.py` | The CLI's Command pattern over `GameController.click(x,y)`. The server has its own command vocabulary mapping to `GameEngine`, not `GameController`. |
| `gui/*` (rendering, animation, hud) | `gui/` | All presentation-layer, pixel/`cv2`-specific; not reusable server-side. |

### Where coupling currently exists (and why it doesn't block the server)

Nothing in `model/`, `rules/`, `realtime/`, or `engine/` imports anything from `io/`, `input/`, or `gui/` — verified across every file read in this review. `GameController` is the only place board/engine/I-O concerns currently meet, and it is entirely excluded from the server plan. This is exactly the separation the specification requires; the server adds new leaves to the dependency tree without pruning anything.

### Which TODOs affect the server plan

Most `TODO(design)` comments added in the two most recent commits (`Position` value object, full `BoardTopology`, `BoardStorage`, `RuleContext`, `PieceDefinition` registry, `InteractionResolver`, `GameAction`, `BoardLayout`) concern board-shape/piece-rule extensibility and do not block a multiplayer server — leave them exactly as deferred. Two are relevant: the `GameAction` TODO (`request_move`/`request_jump` are two hardcoded action shapes) matters only if a future variant needs actions beyond move/jump — not needed for Phases A–E. The "game lifecycle is two plain fields" TODO is directly relevant to `GameSession`, which needs a *third* lifecycle idea the engine doesn't have — "abandoned by disconnect" (technical loss) — modeled at the `GameSession`/`GameService` level, never inside `GameEngine`.

### Should `GameController` be reused or bypassed?

**Bypassed**, per the analysis above and the specification's explicit constraint. `GameService` becomes the new "controller," working directly against `GameEngine` with explicit `(from_row, from_col, to_row, to_col)` commands instead of clicks.

### Is the existing `EventBus` sufficient?

**Partially.** Reusable unchanged as the **per-game domain event bus** (one instance per `GameSession`, injected into that game's `GameEngine`, exactly as `gui/game_loop.py` already does). **Not** sufficient alone as the server's cross-cutting application bus: no event-type discrimination beyond `isinstance`, no correlation/causation IDs or timest-envelope concept, no natural "one bus per game" vs. "one bus for the whole server" split. **Recommendation (unchanged from the first draft, reinforced by the `GameOverEvent` finding above):** keep `EventBus` unchanged, add `GameOverEvent` to its vocabulary, and add a **new, separate** `ApplicationMessageBus` in `messaging/` for server-wide pub/sub. Do not merge the two.

---

## Part 3 — Proposed Architecture

```text
kungfu_chess/
├── model/                     # UNCHANGED — Piece, Board, BoardTopology
├── rules/                     # UNCHANGED — PieceRule, RuleEngine, PromotionRule, WinCondition
├── realtime/                  # UNCHANGED — Motion, RealTimeArbiter, progress_fraction
├── engine/
│   ├── game_engine.py         # UNCHANGED except one new line publishing GameOverEvent [UPDATED]
│   └── events.py              # +GameOverEvent class added alongside MoveResolvedEvent [UPDATED]
├── io/                        # UNCHANGED — BoardParser, BoardValidator, BoardRenderer (reused read-only)
├── input/                     # UNCHANGED — GameController/BoardMapper/commands stay CLI/GUI-only, NOT imported by server/
├── gui/                       # UNCHANGED — presentation layer, untouched
│
├── application/                       # NEW — server-side orchestration, no I/O libraries imported here
│   ├── game_session.py               # GameSession: owns Board+GameEngine+EventBus+lock for one game
│   ├── game_service.py               # GameService: move_request/jump_request -> GameEngine; subscribes to
│   │                                  #   MoveResolvedEvent AND GameOverEvent; publishes GameStartedEvent
│   │                                  #   at session creation [UPDATED]
│   ├── room_service.py                # RoomService: create/join room; creator=White, 2nd joiner=Black,
│   │                                  #   rest=spectators [UPDATED]
│   ├── matchmaking_service.py         # MatchmakingService: queue, ±100 ELO search, timeout
│   ├── auth_service.py                # AuthenticationService: username-only identity (Phase A) then
│   │                                  #   username+password login (Phase B) [UPDATED]
│   ├── rating_service.py              # RatingService: ELO formula, applies exactly once per game
│   ├── connection_service.py          # ConnectionService: disconnect grace period, auto-resign trigger
│   └── dto.py                         # Small dataclasses: BoardSnapshotDTO, GameStateDTO, etc.
│
├── server/                            # NEW — the only package allowed to import an async WebSocket library
│   ├── websocket_gateway.py           # Accepts connections, reads/writes frames, no rule logic
│   ├── connection_manager.py          # Tracks connection_id <-> user_id <-> game_id/room_id
│   ├── schemas.py                     # JSON envelope (de)serialization + validation
│   ├── error_types.py                 # Typed server error enum
│   ├── logging_config.py              # Structured logging setup, server AND client-side conventions [UPDATED]
│   └── server_main.py                 # Composition root: wires everything, starts the event loop
│
├── persistence/                       # NEW — no networking, no game rules
│   ├── repositories.py                # Abstract repository interfaces (Protocols/ABCs)
│   ├── in_memory/                     # Phase A implementations
│   │   └── in_memory_repositories.py
│   └── sqlite/                        # Phase B+ implementations
│       ├── schema.sql
│       ├── sqlite_repositories.py
│       └── migrations.py
│
└── messaging/                         # NEW — the *application* pub/sub, sibling to engine/events.py
    ├── application_message_bus.py      # In-memory pub/sub for cross-cutting server events
    └── application_events.py           # Envelope + event dataclasses, including GameStartedEvent [UPDATED]
```

**File-by-file responsibility (new/changed only):**

- `engine/events.py` **[UPDATED]** — add `GameOverEvent` next to the existing `MoveResolvedEvent` and `EventBus`. No behavior change to `EventBus` itself.
- `engine/game_engine.py` **[UPDATED]** — one additional line in `_resolve_motion`, publishing `GameOverEvent` through `self.event_bus` (if present) at the point `self.game_over = True` is set. Everything else unchanged.
- `application/game_session.py` — the authoritative aggregate for one running game: `Board`/`GameEngine`/`EventBus`, players/spectators, lock, reconnect deadlines, rated flag, sequence number, result.
- `application/game_service.py` — the single place a network move command becomes `GameEngine.request_move(...)`. Subscribes to each game's `EventBus` for both `MoveResolvedEvent` and `GameOverEvent`, re-publishing translated application events; publishes `GameStartedEvent` itself at session creation (not from inside the engine — see Part 5).
- `application/room_service.py` — room lifecycle. **[UPDATED]** Encodes the exact rule from the specification deck: the room creator is assigned White automatically; the second person to join becomes Black; every subsequent joiner is a read-only spectator.
- `application/matchmaking_service.py` — ±100 ELO queue and matching algorithm.
- `application/auth_service.py` — **[UPDATED]** two distinct capabilities staged across phases: `identify(username)` (Phase A — no password, no persistence, purely a display label) and `register`/`login` (Phase B — real credentials, SQLite-backed).
- `application/rating_service.py` — ELO computation and idempotent application.
- `application/connection_service.py` — disconnect grace-period timers and auto-resign trigger. **[UPDATED]** Sends exactly one `player_disconnected` message carrying the total grace period; does not poll or re-send countdown ticks — the client renders its own local countdown from that single value.
- `server/websocket_gateway.py` — accepts a socket, reads/writes JSON frames, delegates every command to the appropriate `application/*` service; zero rule logic.
- `server/connection_manager.py` — tracks live connections and identities; notifies `ConnectionService` on disconnect.
- `server/schemas.py` — envelope parsing/validation; rejects malformed JSON before it reaches any service.
- `server/logging_config.py` **[UPDATED]** — structured logging conventions shared by the server process; a parallel, lightweight client-side logging convention is documented for client implementations to follow (the specification requires logging on *both* sides).
- `persistence/repositories.py` — abstract interfaces only, so `application/*` never imports SQLite directly.
- `messaging/application_message_bus.py` — a second, small in-memory pub/sub, distinct from `engine/events.EventBus`.
- `messaging/application_events.py` **[UPDATED]** — includes `GameStartedEvent` (published by `application/game_service.py`, not the engine), `PlayerJoinedRoomEvent`, `MatchFoundEvent`, `PlayerDisconnectedEvent`, `AutoResignAppliedEvent`, `RatingUpdatedEvent`.

---

## Part 4 — Dependency Rules

```text
        server/  (websocket_gateway, connection_manager, schemas)
              │
              ▼
        application/  (game_service, room_service, matchmaking_service,
                       auth_service, rating_service, connection_service)
              │                              │
              ▼                              ▼
        engine/ (GameEngine, EventBus)   persistence/ (repositories)
              │                              │
              ▼                              ▼
   rules/ , realtime/ , model/          sqlite (only inside persistence/sqlite/)

        messaging/ (ApplicationMessageBus) — used BY application/ and server/,
                    imports nothing from engine/model/rules/realtime.
```

**Allowed dependency directions:**
- `server/` → `application/`, `server/schemas.py`, `messaging/`. Never → `model/`, `rules/`, `realtime/` directly.
- `application/` → `engine/`, `rules/`, `realtime/`, `model/` (read/orchestrate only), `persistence/repositories.py` (interfaces only), `messaging/`.
- `persistence/sqlite/` → stdlib `sqlite3` only. Never imported by anything except `persistence/` itself and `server_main.py` (wiring).
- `engine/`, `rules/`, `realtime/`, `model/` → each other only, exactly as today. **Never** → `application/`, `server/`, `persistence/`, `messaging/`. **[UPDATED]** This rule holds even after the `GameOverEvent` addition: `engine/events.py` gains a new *class definition*, but still imports nothing from outside `engine/`.

**Where things fit:** repositories behind interfaces (`persistence/repositories.py`), consumed by `application/*` via constructor injection; SQLite adapters only inside `persistence/sqlite/`; the `ApplicationMessageBus` instantiated once in `server_main.py` and injected into every producing/consuming service; the WebSocket broadcaster inside `server/websocket_gateway.py` as a *consumer* of the `ApplicationMessageBus`; schemas/DTO mappers kept as two distinct layers (`server/schemas.py` for network⇄application, `application/dto.py` for domain⇄application) — do not collapse them.

**Forbidden imports:**
- `kungfu_chess/model/*`, `kungfu_chess/rules/*`, `kungfu_chess/realtime/*`, `kungfu_chess/engine/*` must **never** import anything from `server/`, `application/`, `persistence/`, or `messaging/`.
- `kungfu_chess/engine/game_engine.py` must never import `websockets`, `sqlite3`, `bcrypt`/`argon2`, `asyncio`, or anything under `server/`.
- `server/websocket_gateway.py` must never import `kungfu_chess.model.board.Board`, `kungfu_chess.rules.rule_engine.RuleEngine`, or any `rules/*` class directly — only `application/game_service.py`.
- `persistence/sqlite/*` must never be imported from `server/` directly — always through `application/*_service.py`.

---

## Part 5 — Domain, Application, and Network Event Model

Three distinct object families, deliberately not unified:

| Layer | Example type | Lives in | Scope | Carries |
|---|---|---|---|---|
| **Domain event** | `MoveResolvedEvent` (existing), `GameOverEvent` **[UPDATED — new]** | `engine/events.py` | One `GameEngine`/`EventBus` instance, one game | `MoveResolvedEvent`: `from_row, from_col, to_row, to_col, moving_piece, captured_piece, timestamp_ms`. `GameOverEvent`: `winner, timestamp_ms` — pure domain values, no `game_id`, no `user_id`, no JSON. |
| **Application event** | `GameStartedEvent` **[UPDATED — new, application-level not domain]**, `GameMoveAppliedEvent`, `GameEndedEvent`, `PlayerJoinedRoomEvent`, `MatchFoundEvent`, `PlayerDisconnectedEvent`, `AutoResignAppliedEvent`, `RatingUpdatedEvent` | `messaging/application_events.py` | Server-wide, `ApplicationMessageBus` | Envelope fields + a reference to the domain event/DTO it was translated from — `game_id`, `room_id`, `user_id` first appear here. |
| **Network message** | `{"type": "move_accepted", ...}` JSON | `server/schemas.py` | One WebSocket connection (or a broadcast set) | JSON-serializable payload only — no Python objects, no `Board`/`Piece` references. |

**Why `GameStartedEvent` is application-level, not domain-level [UPDATED]:** `GameEngine` has no "not yet started" state — the moment it is constructed, it is already a playable game. "Game started" is meaningful only from the server's perspective (a `GameSession` was just created for two matched/connected players), so it is published by `application/game_service.py` at session-creation time, never by `GameEngine` itself. This keeps the domain layer honest: it only ever reports what actually happens *inside a game already in progress*.

**Bus consumers required by the specification, and what feeds them [UPDATED]:**

| Consumer (from the "BUS" slide) | Fed by | Status |
|---|---|---|
| Update Scores | `MoveResolvedEvent` → `GameMoveAppliedEvent` (captured_piece present) | Already works today client-side (`ScoreObserver`); server-side equivalent via `RatingService`/logging. |
| Update Move Logs | `MoveResolvedEvent` → `GameMoveAppliedEvent` | Already works today client-side (`MovesLogObserver`); reusable pattern server-side. |
| Adding sound | `MoveResolvedEvent` (move/capture sounds) + `GameOverEvent` (end-of-game sound) | **Capture/move sound was already possible; end-of-game sound was not, until `GameOverEvent` is added.** |
| Game start/end animations | `GameStartedEvent` (application) for start; `GameOverEvent` (domain, translated to `GameEndedEvent` application event) for end | **Start animation was already impossible (no such event existed anywhere); end animation was impossible for the same reason as the sound gap above.** |

**Where translation occurs:**
1. `GameEngine._resolve_motion` publishes `MoveResolvedEvent` (unchanged) and, **[UPDATED]**, now also publishes `GameOverEvent` on the same per-game `EventBus` the instant `self.game_over` becomes `True`.
2. `GameService` is subscribed to that `EventBus` (constructor-injected exactly like `MovesLogObserver` today) and translates each domain event into an application event on the `ApplicationMessageBus` — `GameMoveAppliedEvent`/`MoveRejectedEvent` from moves, `GameEndedEvent` from `GameOverEvent`, and `GameStartedEvent` published directly by `GameService` itself at session creation (no domain event to translate — see above).
3. `server/websocket_gateway.py` (or a dedicated `Broadcaster`) subscribes to the `ApplicationMessageBus` and produces network messages for the relevant WebSocket connections via `connection_manager`.

---

## Part 6 — WebSocket Protocol

**Recommendation: JSON typed message envelopes**, not raw strings or ad-hoc dicts.

### Envelope shape (every message, both directions)

```json
{
  "type": "move_request",
  "message_id": "c2f3e2b0-...-uuid",
  "correlation_id": "c2f3e2b0-...-uuid",
  "timestamp": 1737300000123,
  "game_id": "g_8f1a2c",
  "payload": { }
}
```

### Client → Server message types

| `type` | `payload` | Notes |
|---|---|---|
| `connect` | `{ "client_version": "1.0", "username": "shiri" }` **[UPDATED]** | `username` here is the Phase A, password-less display label (see Part 11). |
| `login` | `{ "username": "...", "password": "..." }` | Phase B+, distinct message type from `connect`'s username-only identification. |
| `join_game` | `{ "mode": "quick_local" }` (Phase A) or `{ "room_id": "..." }` (Phase E) | |
| `move_request` | `{ "from_row": 6, "from_col": 4, "to_row": 4, "to_col": 4 }` | Explicit source/destination, not pixels, not a click. |
| `jump_request` | `{ "row": 6, "col": 4 }` | |
| `play` | `{ "rated": true }` | Enters matchmaking (Phase C). |
| `cancel_matchmaking` | `{}` | |
| `create_room` / `join_room` **[UPDATED]** | `{}` / `{ "room_id": "..." }` | Maps to the deck's Room/Create/Join buttons. |
| `ping` | `{}` | Liveness. |

### Server → Client message types

| `type` | `payload` (example) |
|---|---|
| `state_snapshot` | `{ "board": [["wR","wN",...],...], "game_over": false, "winner": null, "sequence": 42 }` |
| `move_accepted` | `{ "sequence": 43 }` (correlation_id = the original `move_request`'s `message_id`) |
| `move_rejected` | `{ "reason": "INVALID_MOVE" }` |
| `game_event` | `{ "kind": "capture", "from": [6,4], "to": [4,4], "captured": "bP" }` |
| `game_started` **[UPDATED]** | `{ "white": "playerA", "black": "playerB", "rated": true }` — driven by `GameStartedEvent`, primarily for client-side start animation/sound triggers. |
| `game_over` | `{ "winner": "w", "reason": "king_capture" }` — driven by `GameEndedEvent`, itself driven by the new `GameOverEvent`. |
| `player_disconnected` | `{ "color": "b", "grace_period_ms": 25000 }` **[UPDATED — design note]**: sent exactly once per disconnect; the client is responsible for rendering its own local countdown from `grace_period_ms` — the server does not send repeated per-second tick messages. |
| `matchmaking_success` | `{ "game_id": "g_8f1a2c", "color": "w", "opponent": "player42" }` |
| `matchmaking_timeout` | `{}` |
| `room_update` **[UPDATED]** | `{ "room_id": "...", "white": "...", "black": "...", "spectators": ["..."] }` |
| `error` | `{ "code": "NOT_YOUR_TURN_OR_ACTION", "message": "..." }` |
| `pong` | `{}` |

### Validation, sequencing, duplicates, reconnection
Unchanged from the first draft: reject malformed/oversized/unrecognized messages with `error` (connection stays open); every `state_snapshot`/`board_update`/`game_event` carries a monotonically increasing per-game `sequence`; duplicate `message_id` within a short window replays the cached response instead of reprocessing; reconnection uses one full `state_snapshot` (Part 9), not event replay.

---

## Part 7 — Data Model and SQLite Schema

```sql
CREATE TABLE users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,        -- bcrypt/argon2 hash, includes its own salt
    current_rating  INTEGER NOT NULL DEFAULT 1200,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE rooms (
    room_id      TEXT PRIMARY KEY,
    is_private   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    closed_at    TEXT
);

CREATE TABLE room_members (
    room_id   TEXT NOT NULL REFERENCES rooms(room_id),
    user_id   INTEGER NOT NULL REFERENCES users(user_id),
    role      TEXT NOT NULL CHECK (role IN ('player', 'spectator')),
    joined_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (room_id, user_id)
);

CREATE TABLE games (
    game_id      TEXT PRIMARY KEY,
    room_id      TEXT REFERENCES rooms(room_id),
    rated        INTEGER NOT NULL DEFAULT 0,
    started_at   TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at     TEXT,
    result       TEXT CHECK (result IN ('white_win','black_win','abandoned', NULL)),
    end_reason   TEXT CHECK (end_reason IN ('king_capture','disconnect_timeout','server_restart', NULL))
);

CREATE TABLE game_players (
    game_id  TEXT NOT NULL REFERENCES games(game_id),
    user_id  INTEGER NOT NULL REFERENCES users(user_id),
    color    TEXT NOT NULL CHECK (color IN ('w','b')),
    PRIMARY KEY (game_id, user_id)
);

CREATE TABLE rating_changes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id        TEXT NOT NULL REFERENCES games(game_id),
    user_id        INTEGER NOT NULL REFERENCES users(user_id),
    rating_before  INTEGER NOT NULL,
    rating_after   INTEGER NOT NULL,
    applied_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (game_id, user_id)      -- prevents a duplicate ELO update for the same game+player
);

-- Optional, Phase D+: append-only event log for auditing/debugging only (NOT the reconnection mechanism — see Part 9)
CREATE TABLE game_events_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id   TEXT NOT NULL REFERENCES games(game_id),
    sequence  INTEGER NOT NULL,
    kind      TEXT NOT NULL,
    payload   TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

`password_hash` stores a self-salting bcrypt/argon2 string (no separate `salt` column needed). `current_rating` on `users` is a read-optimized denormalization; `rating_changes` is the source of truth for history and idempotency.

---

## Part 8 — Service-by-Service Design

### `GameService`
- **Responsibility:** the only service calling `GameEngine.request_move`/`request_jump`/`advance_time`. **[UPDATED]** Subscribes to each game's `EventBus` for **both** `MoveResolvedEvent` and the new `GameOverEvent`; publishes `GameStartedEvent` itself at session creation.
- **Dependencies:** `GameSession` registry, `ApplicationMessageBus`, `GameRepository`.
- **Public methods:** `create_session(white_user_id, black_user_id, rated) -> GameSession` (publishes `GameStartedEvent`), `handle_move_request(...)`, `handle_jump_request(...)`, `tick(game_id, elapsed_ms)`.
- **Events produced:** `GameStartedEvent`, `GameMoveAppliedEvent`, `MoveRejectedEvent`, `GameEndedEvent`.
- **Events consumed:** none (produces from domain events + its own lifecycle moments).
- **Transaction boundaries:** persisting a finished game is one transaction, independent of any rating transaction.
- **Concurrency:** every method touching a `GameSession` acquires that session's lock first (Part 9/10).

### `RoomService` **[UPDATED]**
- **Responsibility:** room lifecycle, **explicit color assignment**: the room creator is White; the second joiner is Black; every subsequent joiner is a read-only spectator.
- **Dependencies:** `RoomRepository`, `GameService`, `ApplicationMessageBus`.
- **Public methods:** `create_room(owner_user_id, is_private) -> room_id` (owner recorded as the future White), `join_room(room_id, user_id) -> RoomJoinResult` (assigns Black or spectator based on current membership count), `leave_room(room_id, user_id)`.
- **Events produced:** `RoomCreatedEvent`, `PlayerJoinedRoomEvent`, `PlayerBecameSpectatorEvent`.
- **Failure cases:** `ROOM_NOT_FOUND`, `ROOM_FULL`.
- **Concurrency:** one lock per room for admission decisions under simultaneous joins (deciding who becomes Black vs. the first spectator is a race without this).

### `MatchmakingService`
- Unchanged from the first draft: ±100 ELO queue, configurable timeout, `MatchFoundEvent`/`MatchmakingTimeoutEvent`, single in-process lock.

### `AuthenticationService` **[UPDATED]**
- **Responsibility:** two distinct capabilities, staged: `identify(username) -> DisplayIdentity` (Phase A — no password, no repository, purely a connection-scoped label used to assign White/Black and to label broadcasts/logs) and `register`/`login`/`verify_token`/`logout` (Phase B — real, SQLite-backed credentials).
- **Dependencies (Phase B):** `UserRepository`, a password-hashing adapter, a token strategy.
- **Failure cases:** `USERNAME_TAKEN`, `INVALID_CREDENTIALS`, throttling after N failed attempts.

### `RatingService`
- Unchanged: `apply_result(game_id, white_user_id, black_user_id, result, rated) -> RatingChangeResult`, idempotency check against `rating_changes` before writing, one transaction per call.

### `ConnectionService` **[UPDATED]**
- **Responsibility:** disconnect detection → grace-period timer → auto-resign trigger. Sends exactly one `player_disconnected` message with the total grace period; never sends repeated countdown ticks (client renders its own countdown locally).
- **Dependencies:** `GameService`, `ApplicationMessageBus`.
- **Concurrency:** one timer per disconnected player, atomically cancellable on reconnect under the same per-game lock `GameService` uses.

### `StateSyncService`
- Unchanged: builds `state_snapshot` from the authoritative `GameSession`, read-only.

---

## Part 9 — Game Session and State Ownership

| State | Owner | Notes |
|---|---|---|
| `Board` | `GameSession` | Never held by `server/` or `persistence/` directly. |
| `GameEngine` | `GameSession` | One per game, constructed with the session's own `EventBus`, `RuleEngine()`, `RealTimeArbiter(...)`, `WinCondition` (default `CaptureKingWinCondition`). |
| `EventBus` | `GameSession` | One per game; **[UPDATED]** now carries `MoveResolvedEvent` and `GameOverEvent`; `GameService` subscribes to both. |
| Per-game lock | `GameSession` | An `asyncio.Lock` guarding every mutation path. |
| Player assignments (White/Black) | `GameSession` | Phase A: connection order. Phase C: matchmaking. **[UPDATED]** Phase E rooms: creator=White, second joiner=Black (`RoomService`'s rule, reflected onto the `GameSession` it creates). |
| Spectators | `GameSession` | A read-only set of connection/user IDs; `RoomService` mediates admission, `GameSession` is the source of truth. |
| Connection status | `ConnectionService`, referenced by `GameSession` | Actual socket objects live in `connection_manager`, never inside `GameSession`. |
| Game version / sequence number | `GameSession` | Incremented on every state-changing event from that game's `EventBus`. |
| Reconnect deadline | `ConnectionService`, mirrored on `GameSession` for `StateSyncService` | |
| Persisted result | `GameRepository`, written once by `GameService`/`RatingService` | `GameSession` itself is never persisted as an object. |
| ELO update status | `rating_changes` table (`UNIQUE(game_id, user_id)`) | The actual source of truth; an in-memory flag is only a fast-path optimization. |

**What belongs in `GameSession` vs. `GameEngine`:** `GameEngine` keeps exactly what it has today. `GameSession` adds everything the specification says must not live in the engine: network user identities, the lock, reconnect deadlines, rated flag, room/game IDs. No user authentication or database session object is ever passed into `GameEngine` or `Board`.

**On not persisting `GameEngine` as a blob:** persist the initial board layout (via `BoardParser`'s existing DSL) plus the accepted move list, or simply the final board state and result — never a pickled live object graph.

---

## Part 10 — Time and Concurrency Design (Phase A)

**Concurrency:** a single-process `asyncio` event loop, **one `asyncio.Lock` per `GameSession`** combined with **one dedicated `asyncio.Queue` + one worker coroutine per active game**. A global lock across all games is rejected — unrelated games would serialize for no reason; nothing in `engine/`, `realtime/`, or `model/` holds shared global state.

```text
class GameSession:
    def __init__(self, ...):
        self.lock = asyncio.Lock()
        self.queue = asyncio.Queue()
        self.engine = GameEngine(board, jump_duration_ms, event_bus=self.event_bus)
        self.last_tick_wall_clock = now()

    async def worker_loop(self):
        while not self.closed:
            command = await self.queue.get()
            async with self.lock:
                self._advance_time_lazily()
                result = self._dispatch(command)     # -> engine.request_move / request_jump
                await self._publish_result(command, result)

    def _advance_time_lazily(self):
        elapsed = now() - self.last_tick_wall_clock
        self.last_tick_wall_clock = now()
        self.engine.advance_time(int(elapsed * 1000))
```

**Time management — recommended: Hybrid, not lazy-only.** `Motion` arrivals, cooldown expiry, and airborne-kill timing must be broadcast as soon as they occur in virtual time, not only when a client happens to send a message. Pure lazy advancement would leave an in-flight `Motion` unresolved indefinitely if neither player sends another command. **Recommended combination:** lazy advancement on every incoming command, **plus** a lightweight periodic tick (every 50–100 ms, configurable) that calls `advance_time` only for sessions currently reporting a pending motion/airborne piece/cooldown (`has_pending_move_from`/`is_airborne`/`is_on_cooldown` already expose exactly this) — and stops ticking the instant none of those are true. A central tick loop over *all* games regardless of activity is rejected as unnecessary overhead at this scale.

---

## Part 11 — Phase Roadmap

### Phase A — Single-process server and basic communication **[UPDATED]**
- **Goals:** two local clients, a shell prompt asking for a **username only** (no password — matches the deck's "just for presentation" login step) before connecting, first connector = White / second = Black, structured JSON protocol, server-authoritative moves, broadcast state, **and** the `GameOverEvent` addition to `engine/events.py`/`game_engine.py`.
- **New modules:** `application/game_session.py`, `application/game_service.py`, `application/auth_service.py` (identify-only for now), `server/websocket_gateway.py`, `server/connection_manager.py`, `server/schemas.py`, `server/server_main.py`, `messaging/application_message_bus.py`, `messaging/application_events.py`.
- **Existing files likely to change:** `engine/events.py` (+`GameOverEvent`), `engine/game_engine.py` (one publish call), `requirements.txt` (add a WebSocket library, e.g. `websockets`).
- **Tests first:** a unit test asserting `GameOverEvent` is published exactly once when `game_over` transitions to `True` and never otherwise (regression-safe against all existing `Tests/engine/test_game_engine.py` cases); `GameService.handle_move_request` against a real `GameEngine`; `websocket_gateway` integration test with two in-process fake clients including the username-only `connect` step.
- **Acceptance criteria:** see Part 15.
- **Risks:** direct `Board` access from the gateway; command reordering under concurrent sends; forgetting the `GameOverEvent` gap and building sound/animation consumers that poll instead of subscribe.
- **Dependencies:** none (first phase).
- **Deferred:** real auth/password, persistence, matchmaking, rooms, reconnection.

### Phase B — Authentication and SQLite persistence
- **Goals:** register/login via a shell prompt (explicitly not a GUI, per the specification) with username + password, SQLite-backed users, ELO initialized to 1200.
- **New modules:** `application/rating_service.py` (auth already scaffolded in Phase A, extended here with real credentials), `persistence/repositories.py`, `persistence/in_memory/*`, `persistence/sqlite/*`.
- **Tests first:** `AuthenticationService` unit tests against an in-memory `UserRepository` before SQLite exists; `RatingService` pure-function ELO tests before repository wiring.
- **Acceptance criteria:** unchanged from first draft — no duplicate usernames, no plaintext/reversible password storage, exactly-once rating update verified by attempting a duplicate application.
- **Risks:** SQLite locking under concurrent writes; reversible-encryption temptation (forbidden by spec).
- **Dependencies:** Phase A's `GameService`/`GameSession`.

### Phase C — Matchmaking
- Unchanged from the first draft: ±100 ELO, configurable timeout, fairness/cancellation/race tests.

### Phase D — Network resilience, disconnects, synchronization **[UPDATED]**
- **Goals:** disconnect → grace period (20–30s, configurable) → auto-resign; reconnect restores full state. **Client renders its own countdown from a single `player_disconnected` message** — the server does not re-send ticks.
- **Tests first:** reconnect-before-grace-period; no-reconnect (exactly one technical loss + rating update); reconnect-vs-timeout race.
- **Acceptance criteria:** unchanged from first draft.

### Phase E — Rooms, spectators, and logging **[UPDATED]**
- **Goals:** room creation (`create_room`) generates a room ID shown to the creator; `join_room` admits the second user as Black and every subsequent user as a spectator; **structured logging is implemented on both the server and the client side** (the specification explicitly requires both, not server-only).
- **New modules:** `application/room_service.py` (with the explicit color-assignment rule), `server/logging_config.py`, plus a documented client-side logging convention (correlation/game/room/user/connection/message IDs shared across both sides so a single request can be traced end-to-end).
- **Tests first:** room capacity, spectator `move_request` rejected with `NOT_A_PLAYER` before reaching `GameEngine`, empty-room cleanup, log correlation ID propagation from a client-sent `message_id` through to the server-side log line.
- **Acceptance criteria:** a third joiner to a room is a spectator and cannot mutate the game; every accepted/rejected command produces a correlated log line on the server, and the reference client logs the corresponding sent/received message with the same `message_id`.

---

## Part 12 — Test Strategy

- **Unit tests (domain):** unchanged — `Tests/model`, `Tests/rules`, `Tests/realtime`, `Tests/engine` continue exactly as today. **[UPDATED]** Add one new unit test for `GameOverEvent` publication (exactly once, only on a real win-condition result).
- **Application service tests:** `GameService` (including the new `GameStartedEvent`/`GameOverEvent` subscriptions), `RatingService` as a pure function, `MatchmakingService` with fake rating lists, `RoomService`'s creator=White/second=Black/rest=spectator rule.
- **Repository tests:** shared contract tests run against both `InMemory*Repository` and `SQLite*Repository` implementations.
- **WebSocket integration tests:** full `connect (username) → join_game → move_request → move_accepted/board_update` sequence; `game_started`/`game_over` messages observed by both connected clients.
- **Concurrency tests:** two simultaneous `move_request`s for one game processed strictly in order.
- **Reconnect tests:** mid-motion disconnect/reconnect; grace-period expiry; reconnect-vs-timeout race.
- **Matchmaking tests:** ±100 ELO boundary, timeout, cancellation, duplicate enqueue.
- **Security tests:** oversized/malformed messages, SQL injection attempt in `username`, rate-limited login failures.
- **End-to-end tests:** the full Phase A milestone script (Part 15).

---

## Part 13 — Risk Register

| Risk | Probability | Impact | Mitigation | Phase |
|---|---|---|---|---|
| Race condition: two commands mutate one game concurrently | Medium | High | Per-game `asyncio.Queue` + lock | A |
| Duplicate rating update for one game | Medium | High | `UNIQUE(game_id, user_id)` + application-level idempotency check | B, D |
| Reconnect vs. timeout race | Medium | Medium | Cancel timer inside the same lock that processes reconnection | D |
| Stale client state after missed messages | Medium | Medium | Monotonic `sequence` + full-snapshot-on-reconnect | A, D |
| Out-of-order network messages | Low–Medium | Medium | Sequence numbers, client discards ≤ last applied | A |
| Direct engine/board access from the WebSocket gateway | Medium | High | Forbidden-imports rule + import-graph test | A |
| **[UPDATED] Missing `GameOverEvent` leaves sound/animation consumers unable to detect game end** | High if not addressed | Medium | Add `GameOverEvent` as a Phase A prerequisite, test-covered | A |
| Message Bus handler failure (one subscriber throws) | Low | Medium | `ApplicationMessageBus` catches/logs per-handler exceptions | A |
| SQLite database locking under concurrent writes | Medium | Medium | WAL mode, short transactions, single writer connection | B |
| Server restart loses in-memory games | High (by design A–D) | Medium | Documented limitation; flagged as a product question | A–D |
| Client impersonation | Low if tokens enforced | High | Authorize every `move_request` against the token's `user_id` matching the recorded player color | B |
| Overgeneralizing the domain too early | Medium | Medium | Out of scope; existing `TODO(design)` comments already document these as deferred | all |

---

## Part 14 — Decision Log

| Decision | Alternatives considered | Selected | Reason | Cost / drawback | Future evolution |
|---|---|---|---|---|---|
| Protocol format | Raw strings, untyped dicts, typed JSON envelope | Typed JSON envelope | Needs ack/correlation/error metadata raw strings can't carry | Slightly more verbose | Could add binary format later |
| WebSocket library | `websockets`, FastAPI+Starlette, raw sockets | `websockets` | Minimal footprint, matches "don't overengineer Phase A" | No built-in HTTP routing | Add FastAPI later if a REST surface is wanted |
| Concurrency model | Global lock, per-game lock, per-game actor+queue, thread pool | Per-game `asyncio.Queue` + lock | Isolates unrelated games, avoids thread/GIL complexity | Slightly more moving parts than "just a lock" | Shard across processes later if CPU-bound |
| Time advancement | Central tick, per-game task, lazy-only, hybrid | Hybrid | Lazy-only silently stalls in-flight motions with no client traffic | Slightly more code than lazy-only | Tick interval configurable |
| State sync on reconnect | Full snapshot, snapshot+replay, pure replay | Full snapshot only | Board state is small; simplest correct option | Slightly more bytes per reconnect | Snapshot+delta later if it grows |
| Message Bus | Reuse `EventBus` for everything, external broker, new sibling bus | New `ApplicationMessageBus`, `EventBus` untouched except `GameOverEvent` | `EventBus` correctly scoped to one game; app events need envelopes/IDs it lacks | Two bus concepts to explain | Swap internals for a real broker later without interface change |
| Password hashing | Plaintext (forbidden), reversible encryption (forbidden), bcrypt, argon2 | bcrypt (argon2 acceptable) | Well-understood, adequate for this threat model | Slower than a naive hash (intentional) | Migrate to argon2id later without schema change |
| `GameController` reuse | Reuse `.click()`, bypass entirely | Bypass — call `GameEngine` directly | Verified pixel/click/single-selection design unsuitable for a server | None — `GameEngine`'s API already fits | N/A |
| **[NEW] `GameOverEvent` addition** | Leave engine unchanged and poll `engine.game_over` from the application layer; add a domain event | Add `GameOverEvent` to `engine/events.py` | The specification's bus requires sound/animation consumers, which cannot be built on polling without defeating the pub/sub model; the change is two lines and fully backward-compatible | One new, tiny, test-covered class in a file that otherwise doesn't change | If more lifecycle events are ever needed (pause, draw, etc.), follow the same pattern |
| **[NEW] `GameStartedEvent` layering** | Model as a domain event inside `GameEngine`; model as an application event | Application event, published by `GameService` | `GameEngine` has no "not started yet" state — there is nothing for it to report | None | N/A |
| **[NEW] Staged login (username-only, then username+password)** | Build full auth from the start; build no identity concept until Phase B | Two explicit steps matching the product deck | The deck explicitly calls out a presentation-only username step before real credentials | One extra small milestone, not real extra cost | `identify()` naturally retires once `login()` exists |
| **[NEW] Disconnect countdown UX** | Server sends a per-second countdown tick; server sends one value, client counts down locally | Single value, client-side countdown | Avoids unnecessary repeated network traffic/state on the server for a purely cosmetic timer | None significant | N/A |
| **[NEW] Room color assignment** | Leave ambiguous ("first two are players"); explicit creator=White rule | Creator = White, second joiner = Black, rest = spectators | Matches the product deck precisely | None | N/A |

---

## Part 15 — Exact Recommended First Milestone **[UPDATED]**

**Scope:** a local single-process WebSocket server (`server/server_main.py`), no database, no real authentication (username-only identification per Phase A), no matchmaking. Two client scripts connect to `ws://localhost:<port>`, each prompted in its shell for a username before connecting.

**Acceptance criteria:**
1. Each client is prompted for a username (no password) before sending `connect`; the server accepts both and, on `join_game`, assigns the first connector White and the second Black.
2. Both clients receive an initial `state_snapshot` with `sequence: 0` and the standard starting board.
3. White sends a legal `move_request`; server replies `move_accepted` (correlation matches the request's `message_id`) to White, and both clients receive `board_update`/`game_event` once the `Motion` resolves via the hybrid tick.
4. Black attempting to move a White piece receives `move_rejected` (`NOT_YOUR_TURN_OR_ACTION`), and `GameEngine.board` is provably unchanged.
5. A structurally illegal move is rejected via `RuleEngine.is_legal` (through `GameService`, never re-implemented in the gateway) with `move_rejected`/`INVALID_MOVE`.
6. A capture of the opposing King ends the game: **[UPDATED]** the test asserts (a) both clients receive `game_over` with the correct winner, (b) the game's `EventBus` is observed (via a test subscriber) to have received exactly one `GameOverEvent`, proving the new domain event fires correctly, and (c) `GameSession`'s state matches `GameEngine.game_over`/`winner` exactly.
7. No test or code path in this milestone imports `sqlite3`, `bcrypt`/`argon2`, or any password concept.
8. An automated test asserts `server/websocket_gateway.py` has no import from `kungfu_chess.model` or `kungfu_chess.rules`.

---

## Part 16 — Questions That Must Be Answered Before Implementation

1. Does this game ever produce a **draw**? The current `WinCondition`/`GameEngine` model has no draw concept at all — should rating support draws, or is every rated game guaranteed to resolve to a win/loss (including technical losses)?
2. Are the existing CLI (`main.py`) and GUI (`gui_main.py`) expected to eventually become network clients of this server, or does the server ship with its own separate (shell-based, per the deck) client, leaving CLI/GUI as permanent offline modes?
3. What is the intended authentication transport for the first WebSocket message — a token inside the `login` payload, or an HTTP-level handshake before the WebSocket upgrade?
4. Is a maximum total game duration or per-move clock intended for a future phase, beyond the disconnect grace period?
5. Should unrated ("casual") games exist at all, or is every server-created game rated by default?
6. Should the ±100 ELO matchmaking range expand over time for a waiting player, and if so, by how much per interval, or should it stay fixed until timeout?
7. Is a browser-based client anticipated (requiring WebSocket origin validation and likely `wss://`), or are clients exclusively trusted, same-machine/LAN Python clients?
8. Is losing all in-progress games on a server restart acceptable through Phase D, or is crash-recoverable game state a hard requirement that should pull persistence earlier?
9. **[NEW]** Should `game_started` also be broadcast as a client-visible network message in Phase A (for sound/animation), or is it only needed internally at first, with the network message added when a client that actually plays a start animation exists?

---

*End of plan. Part 17 (the standalone Claude Code Planning Prompt) is provided separately in the chat message body, not in this file, per request.*
