# Kung Fu Chess — Multiplayer Server Master Plan v2 (Merged, Post-Phase-A)

**Purpose of this file:** a single, implementation-ready plan for Claude Code (running in VS Code, inside this repository) to continue the multiplayer server work. It merges two prior planning documents — this project's own `Multiplayer_Server_Architecture_Plan.md` (verified directly against the current source) and a colleague's independently-written plan for the same product brief — and re-bases both against the code **as it actually stands today**, not as either plan assumed it would stand.

**Verification method:** every claim below about "what already exists" was confirmed by reading the actual files in this repository (not inferred from either source plan), and by running the test suite. Every claim about "what's still missing" was confirmed by the absence of the corresponding file/class/table.

**Verified current status (do not re-derive Phase A — it is done):**
- Latest commit: `7e2ac68` — *"Implement Phase A of the multiplayer server: WebSocket gateway, application layer, GameOverEvent."*
- Test suite: **494 passed**, 2 pre-existing failures unrelated to this work (both are sandbox/subprocess path issues in `Tests/io/test_board_parser.py` and `Tests/test_main.py`, not server code).
- Packages that exist and are populated: `kungfu_chess/messaging/` (`application_events.py`, `application_message_bus.py`), `kungfu_chess/application/` (`game_session.py`, `game_service.py`, `dto.py`), `kungfu_chess/server/` (`schemas.py`, `connection_manager.py`, `websocket_gateway.py`, `server_main.py`, `reference_client.py`), `Tests/server/` (`test_connection_manager.py`, `test_import_boundaries.py`, `test_schemas.py`, `test_websocket_gateway.py`).
- `requirements.txt` already includes `websockets` and `pytest-asyncio`.
- The engine layer (`model/`, `rules/`, `realtime/`, `engine/`) is untouched except for the additive `GameOverEvent` in `engine/events.py` and its single publish call in `engine/game_engine.py::_resolve_motion` — exactly as both source plans recommended, and it is done.

**What this plan is for, concretely:** picking up from here — real authentication + persistence, ELO/matchmaking, disconnect/reconnect resilience, rooms/spectators, structured logging — while locking in one requirement neither source plan stated as an explicit, testable guarantee: **the two players' boards must never disagree.** Section 3 below makes that a first-class architectural requirement, not an assumed side-effect of "the server is authoritative."

---

## 1. The Client/Server Split — Restated as a Hard Rule

This project's entire multiplayer design rests on one split, and every phase below must preserve it:

- **The server owns all logic.** `GameEngine`, `RuleEngine`, `RealTimeArbiter`, `WinCondition`, `PromotionRule` — every rule about what is legal, when a motion arrives, when a game ends — runs **only** inside the server process, inside `GameSession`/`GameService`. No client process ever constructs a `GameEngine` or imports `kungfu_chess.rules`/`kungfu_chess.realtime`/`kungfu_chess.model` for decision-making purposes.
- **The UI is a client, and a client only renders and requests.** A client's only two jobs are: (1) draw whatever board state the server most recently sent, and (2) turn a player's input (a click, a keypress) into a `move_request`/`jump_request` message sent to the server. A client never decides "is this move legal," never decides "did I just capture something," never decides "is the game over" — it only ever *displays* what the server already decided, via `state_snapshot`/`game_event`/`game_over` messages.
- **This is already true of Phase A as built.** `server/websocket_gateway.py`'s own module docstring states it directly: "zero rule logic of its own... board state only ever reaches this module already serialized, via `application.dto`." `Tests/server/test_import_boundaries.py` enforces this with an AST-based static check that `websocket_gateway.py` never imports `kungfu_chess.model`/`kungfu_chess.rules`/`kungfu_chess.realtime`. Every phase from here on (B–E) must extend this rule to new server modules (auth, matchmaking, rooms) — none of them import model/rules/realtime either; they only ever call into `GameService`, which is still the sole caller of `GameEngine.request_move`/`request_jump`/`advance_time`.
- **Consequence for the reference client:** `server/reference_client.py` (already built) is the pattern every future client implementation should follow — it holds no board-legality logic, only a socket connection and message send/receive.

---

## 2. Sources and How They Were Reconciled

| Source | What it got right that the other didn't | Where this plan follows it |
|---|---|---|
| This project's own plan (already implemented as Phase A) | Verified every claim against actual file contents rather than a generic template; correctly identified the `GameOverEvent` gap and fixed it; correctly bypassed `GameController`/`BoardMapper` as unsuitable for a server. | Sections 4, 5, 6, 7 (current-state description) |
| Colleague's plan (`master_work_plan.md`) | A more rigorous *locked-decisions* discipline (16 fixed constraints resolving every open gameplay ambiguity: no draws, fixed ELO band, room-code format, spectator cap, RAM-only persistence scope, trusted-LAN-only transport); an explicit Player Session State Machine diagram; a formal Snapshot Synchronization Strategy; `protocol_version` on every message. | Sections 3, 8 (Locked Decisions), 9 (state machine), 10 (roadmap phases B–E) |

Where the two plans described the *same* thing differently (e.g. both independently proposed a `GameSession` aggregate root, a domain/application event split, a hybrid hidden hidden the same "tick only if something is moving" idle-skip rule), this plan uses **the version already built** and cites the colleague's plan only where it adds a decision Phase A's code doesn't yet need to make (auth, ELO, rooms).

---

## 3. Board Synchronization Guarantee (new requirement — read this section first)

The product is two players, each on their own machine, each looking at their own rendering of the same board. **If the two boards can ever disagree, the game is broken**, independent of whether individual moves are "correct." This section makes that guarantee explicit, names the exact mechanism that already provides it in Phase A, and states what must be added in later phases to keep it true.

### 3.1 The guarantee, stated precisely

At any point in wall-clock time where both clients have processed every message the server has sent them, **both clients' locally-rendered boards must be pixel-for-pixel derivable from the identical `state_snapshot`/`game_event` sequence** — not "similar," not "eventually consistent," but identical, because there is exactly one authoritative board (`GameSession.engine.board`) and both clients are pure read-only observers of it.

### 3.2 Why this already holds in Phase A, mechanism by mechanism

1. **Single source of truth.** There is exactly one `Board` per game, owned by exactly one `GameSession`, mutated by exactly one `GameEngine._resolve_motion` (verified: `Board.set_cell` has no other caller anywhere in the codebase). No client ever holds a second, independently-mutated copy of board state — it only holds whatever it last received.
2. **Monotonic sequence numbers.** `GameSession.sequence` (an `int`, starting at 0) is incremented exactly once per `GameMoveAppliedEvent` broadcast (`GameSession.next_sequence()`, called from `WebSocketGateway._broadcast_move`). Every `state_snapshot` and every `game_event` message carries the current `sequence` value. **This is the mechanism a client uses to detect it has missed something**: if a client ever receives `sequence: N` immediately after previously having `sequence: M` where `N != M + 1`, it knows a message was dropped and must not render past that point silently.
3. **Full-snapshot-on-join, not event-replay.** When a game starts, `WebSocketGateway._handle_join_game` sends **the same, identical `state_snapshot` envelope** to both White and Black — not two independently-constructed snapshots. This is the single most important synchronization guarantee in the whole system: both clients start from **one shared object**, serialized once, sent twice.
4. **Every mutation is broadcast, not per-player-computed.** `_on_game_move_applied`/`_broadcast_move` and `_on_game_ended`/`_broadcast_game_ended` iterate `connections_in_game(game_id)` and send the **same envelope** to every connection in that game — never a player-specific view of the move. There is no code path where White's client and Black's client could receive different data describing the same event.
5. **The hybrid tick keeps in-flight motions synchronized without a client command.** Because `RealTimeArbiter`/`Motion` resolve on virtual time, and `server_main.py`'s `_tick_loop` calls `GameService.tick` for any session with `has_pending_activity()` (pending motion, airborne piece, or active cooldown) regardless of whether either client just sent a message, **a motion that both clients are watching animate resolves and broadcasts at the same virtual-clock moment for both of them** — neither client's local animation timer is authoritative for *when* a move actually completes; only the server's tick is.
6. **Authorization never depends on which client asked.** `GameService.handle_move_request`/`handle_jump_request` authorize by `session.color_for(requester) == piece.color` — the same rule, applied identically regardless of which of the two connected clients sent the request. There is no per-client special-casing that could cause one client's request to be processed differently from an equivalent request by the other.

### 3.3 What is *not yet* guaranteed, and must be added in later phases

| Gap | Why it matters for board sync specifically | Phase that must close it |
|---|---|---|
| No reconnect path yet. If a client's socket drops mid-game, it never gets a fresh `state_snapshot` on return — it has no way to resynchronize. | A silently-desynced client after a reconnect is the single most likely real-world board-mismatch bug in this whole project. | Phase D (Section 10.4) — reconnect handler must send one full `state_snapshot` immediately upon rebind, **not** a partial diff and **not** replayed events. |
| No duplicate-message / retry idempotency yet. A client that resends a `move_request` after a slow/absent `move_accepted` (e.g. a flaky connection) could cause the same move to be interpreted twice if the transport retries. | A duplicated move applied twice would desync the two boards even though the server logic itself is correct. | Phase B/C hardening (Section 10.6) — `message_id`-based duplicate detection in `server/schemas.py` or the gateway's dispatch path, replaying the cached response instead of reprocessing. |
| No `protocol_version` field on the envelope yet (`server/schemas.py::make_envelope` does not include it). | Not a sync bug today, but if the wire format ever changes (e.g. new fields added to `state_snapshot`), an old client silently misinterpreting a new envelope shape is a desync risk with no way to detect it. | Cheap to add now; recommended as a Phase B prerequisite (Section 8, Decision table). |
| No automated test asserts "both connected clients received an identical `state_snapshot` payload." | This guarantee is currently true by construction (Section 3.2), but nothing regresses-tests it — a future refactor of `_broadcast`/`_handle_join_game` could silently break it. | Add immediately, independent of any phase (Section 3.4). |

### 3.4 Required new test (add before or alongside Phase B, not deferred)

A WebSocket integration test — extending `Tests/server/test_websocket_gateway.py` — that: connects two fake clients, completes `join_game`, captures **both** clients' received `state_snapshot` messages and asserts they are byte-for-byte identical (`board`, `sequence`, `game_over`, `winner` all equal); then performs a move and asserts both clients' subsequent `game_event` messages are also byte-for-byte identical and carry the same `sequence`. This is the automated form of the guarantee in Section 3.1 and should be treated as a required regression gate for every phase from here on — any change to `_broadcast`/`dto.build_state_snapshot` that breaks this test is a synchronization regression, full stop.

---

## 4. Verified Current Architecture (Phase A, as built)

```text
kungfu_chess/
├── model/, rules/, realtime/          # UNCHANGED
├── engine/
│   ├── game_engine.py                 # UNCHANGED except the GameOverEvent publish call (done)
│   └── events.py                      # MoveResolvedEvent, GameOverEvent, EventBus (done)
├── io/, input/, gui/                  # UNCHANGED, not imported by server/
│
├── application/                       # DONE
│   ├── game_session.py                # GameSession: Board+GameEngine+EventBus+asyncio.Lock+sequence
│   ├── game_service.py                # GameService: sole caller of request_move/request_jump/advance_time;
│   │                                  #   translates domain->application events; owns session registry
│   └── dto.py                         # build_state_snapshot(session) -> JSON-serializable dict
│
├── messaging/                         # DONE
│   ├── application_events.py          # GameStartedEvent, GameMoveAppliedEvent, MoveRejectedEvent, GameEndedEvent
│   └── application_message_bus.py     # ApplicationMessageBus: type-keyed subscribe, per-handler try/except+log
│
└── server/                            # DONE (Phase A scope only)
    ├── schemas.py                     # make_envelope/encode/decode, MalformedMessageError
    ├── connection_manager.py          # connection_id <-> socket/identity/game_id
    ├── websocket_gateway.py           # quick_local pairing only; zero rule logic; import-boundary tested
    ├── server_main.py                 # composition root + hybrid tick loop (TICK_INTERVAL_MS=75)
    └── reference_client.py            # example client, no rule logic
```

**Not yet built (this plan's remaining scope):** `application/room_service.py`, `application/matchmaking_service.py`, `application/auth_service.py`, `application/rating_service.py`, `application/connection_service.py` (disconnect/reconnect), `persistence/` (does not exist yet at all — no `repositories.py`, no SQLite), `server/logging_config.py`. None of these exist in the repo today; every reference to them below is a **plan**, not a description of current code.

---

## 5. Dependency Rules (verified, must hold through every future phase)

```text
        server/  (websocket_gateway, connection_manager, schemas, [future] logging_config)
              │
              ▼
        application/  (game_service, game_session, [future] room_service, matchmaking_service,
                       auth_service, rating_service, connection_service)
              │                              │
              ▼                              ▼
        engine/ (GameEngine, EventBus)   [future] persistence/ (repositories)
              │                              │
              ▼                              ▼
   rules/, realtime/, model/           sqlite (only inside persistence/sqlite/, once it exists)

        messaging/ (ApplicationMessageBus) — used by application/ and server/,
                    imports nothing from engine/model/rules/realtime. (verified, unchanged)
```

**Forbidden imports (already enforced for Phase A by `Tests/server/test_import_boundaries.py`; extend this test file, don't create a parallel mechanism, as new server modules are added):**
- `model/`, `rules/`, `realtime/`, `engine/` must never import anything from `server/`, `application/`, `persistence/`, or `messaging/`.
- `server/websocket_gateway.py` (and any future `server/*` module) must never import `kungfu_chess.model.board.Board`, `kungfu_chess.rules.rule_engine.RuleEngine`, or any `rules/*`/`realtime/*` class directly — only through `application/game_service.py`.
- Once `persistence/` exists: `persistence/sqlite/*` must never be imported from `server/` directly — always through an `application/*_service.py`.

---

## 6. Event & Message Architecture (verified current + refinements adopted for later phases)

### 6.1 Three layers (unchanged, verified against actual source)

| Layer | Verified example | Lives in | Scope | Carries |
|---|---|---|---|---|
| Domain event | `MoveResolvedEvent`, `GameOverEvent` | `engine/events.py` | One `GameEngine`/`EventBus`, one game | No `game_id`/`user_id` |
| Application event | `GameStartedEvent`, `GameMoveAppliedEvent`, `MoveRejectedEvent`, `GameEndedEvent` | `messaging/application_events.py` | Server-wide, `ApplicationMessageBus` | `game_id`/`user_id` first appear here |
| Network message | `state_snapshot`, `game_event`, `move_accepted`, etc. | `server/schemas.py` envelope | One connection or a broadcast set | JSON only, no Python objects |

### 6.2 Refinements adopted from the colleague's plan for future phases

- **`protocol_version` on every envelope** — add as a Phase B prerequisite (see Section 3.3): `make_envelope` gains a `protocol_version` field, sourced from config (Section 11), defaulting to `1`. Cheap now, expensive to retrofit once real clients exist outside this repo.
- **Snapshot cadence is not a separate timer** — already true by construction: the hybrid tick (Section 3.2, point 5) *is* the resync cadence while something is moving; there is no separate "every N seconds, resend a snapshot" timer to build, and none should be added — it would be redundant with the idle-skip tick rule already implemented.
- **Rooms/matchmaking transport events belong in `messaging/application_events.py`, added only when their consumer (Phase C/E) is being built** — do not pre-declare `MatchFoundEvent`/`PlayerJoinedRoomEvent`/etc. now; follow the same incremental pattern that produced `GameStartedEvent`/`GameEndedEvent` in Phase A (a type is added exactly when a producer and consumer for it both exist).

---

## 7. Locked Architectural Decisions for Phases B–E

These are fixed constraints for everything from here on, adopted from the colleague's plan (they resolve every open gameplay ambiguity in the product brief) and cross-checked against what Phase A already assumes. None contradict the current codebase.

| # | Decision | Phase | Consistent with current code? |
|---|---|---|---|
| 1 | Server remains a single process, single-threaded `asyncio` event loop. No threads/multiprocessing for game/connection handling. | all | Yes — `server_main.py` already this shape. |
| 2 | The shell/CLI login (username, then username+password) is the **permanent** auth interface — not a placeholder for a future GUI login screen. | B | Extends Phase A's password-less `connect{username}` (already built) with a real login step. |
| 3 | Passwords hashed (PBKDF2-HMAC-SHA256 from stdlib `hashlib`, or bcrypt/argon2) before persistence — never plaintext. | B | New. |
| 4 | ELO: standard logistic expected-score formula, single fixed configured K-factor. No variable K. | C | New. |
| 5 | Matchmaking timeout → client returns to explicit **idle** state, no auto-retry. | C | New. |
| 6 | "Play" matchmaking supports exactly 2 connections; a third is rejected outright. Spectators never permitted in Play, only in Rooms. | C/E | New; Phase A's `quick_local` pairing already caps at 2 by construction (only two roles: waiting/paired) — the rule generalizes cleanly. |
| 7 | A disconnected player has 20 seconds to reconnect and resume the **exact same** game state, via a session token issued at login — not by re-authenticating. | B/D | New; depends on Decision 2/3 existing first. |
| 8 | Room IDs: short human-readable alphanumeric codes (4–6 chars), collision-checked against active rooms — not UUIDs. | E | New. |
| 9 | Rooms cap spectators at 20; room destroyed immediately once both players have left. | E | New. |
| 10 | SQLite persistence scoped strictly to: user accounts, session tokens, current ratings. No move/match/room-history tables. | B | New — `persistence/` package does not exist yet. |
| 11 | Structured logs are NDJSON, local files only, on **both** client and server. | E (scaffolding earlier) | New. |
| 12 | Rated games never end in a draw — every completed game resolves to a definite win/loss, including forfeits. No `0.5` path anywhere. | C | Consistent — `WinCondition`/`CaptureKingWinCondition` already has no draw concept. |
| 13 | The ±100 ELO matchmaking band is fixed for the whole search window; it never widens while waiting. | C | New. |
| 14 | Every server-created game is rated (Play and Room alike); only spectators are excluded from rating effects. | C/E | New. |
| 15 | Server targets trusted, same-machine/LAN Python clients only for this scope — no browser client, no WS origin validation, no TLS/`wss://`. | all | Consistent — Phase A already uses plain `ws://` via `websockets`. |
| 16 | All live game/connection/queue state lives in server process memory only. Losing in-progress games on restart is an accepted, deliberate tradeoff. | all | Consistent — `GameService._sessions` is already a plain in-memory dict with no persistence. |

---

## 8. Player Session State Machine (adopted, adapted to actual module names)

```text
            (Phase B CLI login: username, then username+password)
                   │ success
                   ▼
                 IDLE ───────────────────────────┐
                   │ press "Play"                 │ Room Create/Join (Phase E)
                   ▼                               ▼
             MATCHMAKING (Phase C)            PLAYING (Room)
             │           │                          │
    match found     1-min timeout                   │
    (Decision 6)   (Decision 5 -> IDLE,              │
                    no auto-retry)                   │
                   ▼                                  │
             PLAYING (Play) ◀────────────────────────┘   (same states from here on)
                   │
        connection drops (Phase D)
                   ▼
         DISCONNECTED (20s grace — Decision 7)
             │                          │
    reconnect in time            20s elapse, no reconnect
             ▼                          ▼
    PLAYING (resumed,                FORFEITED
    exact same GameSession)              │
             │                           ▼
    game ends normally          rating updated (Decision 4/12)
             ▼                          │
     rating updated ◀───────────────────┘
     (Decision 4/12)
             │
             ▼
            IDLE
```

Every transition above must preserve the Board Synchronization Guarantee (Section 3): in particular, the `DISCONNECTED → PLAYING (resumed)` transition is exactly the reconnect path flagged in Section 3.3 as the highest-risk desync gap today.

---

## 9. Data Model — SQLite Schema (Phase B, does not exist yet)

```sql
CREATE TABLE users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,        -- PBKDF2/bcrypt/argon2, self-salting or with a paired salt column
    password_salt   TEXT,                 -- only needed if using PBKDF2-HMAC (bcrypt/argon2 embed their own)
    rating          INTEGER NOT NULL DEFAULT 1200,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE sessions (
    token           TEXT PRIMARY KEY,     -- secrets.token_urlsafe(), the sole reconnection identity (Decision 7)
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    issued_at       TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Per Decision 10: nothing beyond these two tables. No games/rooms/rating_changes
-- history tables — rating is a live column on `users`, updated in place, not archived.
```

This intentionally drops this project's own earlier draft's `rooms`/`games`/`game_players`/`rating_changes`/`game_events_log` tables — the colleague's plan's Decision 10 is stricter and is adopted here: **no history tables of any kind**, only `users` and `sessions`. If per-game audit history is wanted later, that is a deliberate future decision, not silently reintroduced here.

**Idempotent rating application without a history table:** since Decision 10 forbids a `rating_changes` audit table, exactly-once rating application (needed regardless — Section 10.3) must be guarded by an in-memory flag on `GameSession` (e.g. `rating_applied: bool`), checked and flipped atomically under the session's existing `asyncio.Lock`, not by a database-level `UNIQUE` constraint. This is a deliberate consequence of adopting Decision 10 as-is — flag it to the user if a persisted audit trail is later wanted, since that would reopen Decision 10.

---

## 10. Phase Roadmap (Phases B–E, from the current, verified Phase-A baseline)

### 10.1 Phase B — Authentication & Persistence

**Goal:** replace Phase A's password-less `connect{username}` with the permanent CLI login flow (Decision 2), hashed passwords (Decision 3), SQLite-backed accounts and ratings (Decision 10), session tokens (Decision 7, consumed fully in Phase D).

**New modules:**
- `kungfu_chess/persistence/repositories.py` — `UserRepository`/`SessionRepository` interfaces (Protocols/ABCs).
- `kungfu_chess/persistence/sqlite/sqlite_repositories.py` — the only place `sqlite3` is imported.
- `kungfu_chess/persistence/sqlite/schema.sql` + a small bootstrap/migration function.
- `kungfu_chess/application/auth_service.py` — `AuthenticationService.register`/`login`/`resolve_token`; wraps password hashing (stdlib `hashlib.pbkdf2_hmac`, per-user salt, iteration count from config).
- `kungfu_chess/server/cli_login_flow.py` (client-side) — `AWAITING_USERNAME → AWAITING_PASSWORD → AUTHENTICATED` state machine, run before the WebSocket handshake.

**Changed modules:**
- `server/websocket_gateway.py::_handle_connect` — replace the current password-less `set_identity` call with a call into `AuthenticationService`, receiving a session token back instead of a bare username string. **`GameSession.color_for`/`white`/`black` continue to be plain display-name strings exactly as today** — only the identification step gains real credentials; the authorization logic in `GameService.handle_move_request` (Section 3.2 point 6) does not need to change shape, only what populates `white`/`black`.

**Required test additions:** `AuthenticationService` unit tests against an in-memory `UserRepository` fake before SQLite exists; duplicate-username registration produces a clean rejection, not a crash; a repository contract test suite run against both the in-memory fake and the real `SqliteUserRepository` (so a future swap doesn't silently change behavior).

**Risk carried over from Section 3.3:** add `protocol_version` to `make_envelope` in this phase, since the wire format is already being touched (`connect`'s payload shape changes).

### 10.2 Phase C — Matchmaking & ELO Rating

**Goal:** a "Play" flow searching ±100 ELO (Decision 13) for up to 1 minute (Decision 5), rating starting at 1200, updated via the standard logistic formula with a fixed K-factor (Decision 4), no draws (Decision 12), every game rated (Decision 14).

**New modules:**
- `kungfu_chess/application/rating_service.py` — pure functions `expected_score(a, b)`/`update_rating(rating, expected, actual, k)`; `actual` is always exactly `1.0` or `0.0`.
- `kungfu_chess/application/matchmaking_service.py` — enqueue/scan/dequeue on match-or-timeout; the ±100 band is read once at enqueue time and never widened (Decision 13, an explicit no-op to implement, not an omission).

**Changed modules:**
- `GameService.create_session` gains a `rated: bool` concept feeding `rating_service` on `GameEndedEvent`.
- `websocket_gateway.py` gains `play`/`cancel_matchmaking` handlers alongside the existing `join_game` (quick_local remains available for local/offline-style testing — it is not replaced, matchmaking is a new, separate join path).

**Required test additions:** ELO pure-function tests (boundary cases, always-integer or always-defined outputs); a test that a Room-originated game (Section 10.4) still triggers `RatingService` identically to a Play-originated game (Decision 14 — easy to accidentally wire only to matchmaking); a race test for "two players timing out and matching in the same instant" needing an atomic claim step in the queue.

### 10.3 Phase D — Reconnection & Resilience (closes the Section 3.3 gap)

**Goal:** disconnect → single `player_disconnected` message with `grace_period_ms` (not repeated countdown ticks — client renders its own local countdown) → 20-second reconnect window resuming the exact `GameSession` (Decision 7) → auto-forfeit via the same `GameEndedEvent`/rating path as any other result if the window elapses.

**New modules:**
- `kungfu_chess/application/connection_service.py` — records disconnect on the affected `GameSession`, starts a cancellable timer (value from config), does **not** pause `GameEngine`/`RealTimeArbiter` (the game keeps running in real time even while one player is disconnected — confirm this is the intended UX before implementing, per the colleague's plan's own flagged note).
- A reconnect handler recognizing a returning session token, rebinding the new socket to the existing `GameSession`'s player slot, and — **critically for Section 3.1** — sending one full `state_snapshot` immediately upon rebind, exactly as `_handle_join_game` already does for a fresh join. Do not implement this as an event replay; reuse `dto.build_state_snapshot` unchanged.

**Required test additions:** the Section 3.4 synchronization test extended to a reconnect scenario — after a simulated disconnect/reconnect, the reconnecting client's newly-received `state_snapshot` must exactly match the still-connected opponent's last-known state (same `sequence`, same `board`); reconnect-after-window-elapsed sees a fresh-login flow instead; a duplicate-`message_id` retry (Section 3.3) does not double-apply a move.

### 10.4 Phase E — Rooms, Spectators, Structured Logging

**Goal:** Room create/join dialog (creator = White, second joiner = Black, everyone after = read-only spectator, per the product deck and both source plans), 20-spectator cap, immediate teardown on both-players-gone, NDJSON structured logging on **both** server and client (Decision 11).

**New modules:**
- `kungfu_chess/application/room_service.py` — `create_room`/`join_room`/`leave_room`; room-ID generation (4–6 char alphanumeric, collision-checked, Decision 8) in its own small module so the code scheme can change independently.
- `kungfu_chess/server/logging_config.py` — one NDJSON logging setup used by every server module (never ad hoc `print`/inconsistent `logging.getLogger` formatting); every log line tagged with `message_id`/`game_id`/hashed session token for end-to-end correlation.
- A documented, mirrored client-side logging convention (same NDJSON shape, same `message_id` correlation) — `server/reference_client.py` should be updated to demonstrate it, since it is the example every future client implementation follows.

**Changed modules:** `websocket_gateway.py` gains `create_room`/`join_room` handlers; the existing `_broadcast`/`connections_in_game` helpers already generalize cleanly to "everyone in this game, players and spectators alike" — spectators are just additional entries returned by `connections_in_game`, not a special case, provided the gateway also rejects `move_request`/`jump_request` from a non-player role (new authorization check, alongside the existing color-ownership check in `GameService`).

**Required test additions:** spectator `move_request` rejected before reaching `GameEngine`; empty-room teardown; the 21st spectator rejected with an explicit message; **and** the Section 3.4 synchronization test extended to 3+ connections (all spectators plus both players receive an identical `state_snapshot`/`game_event` stream — this is where the "boards must match" guarantee gets hardest to hold, since it now applies across more than two observers).

---

## 11. Configuration Hierarchy (adopted, applies from Phase B onward)

Do not grow one flat `ServerConfig`. Split by concern, matching the existing `GameConfig` accessor convention already used for board/motion constants:

- `NetworkConfig` — host, port, `protocol_version`.
- `AuthenticationConfig` — PBKDF2 iteration count, session token lifetime.
- `RatingConfig` — base rating (1200), K-factor, ELO band (±100).
- `RoomConfig` — room-code length, spectator cap (20).
- `ReconnectConfig` — grace period (20s).
- `LoggingConfig` — log file paths, rotation policy.
- A top-level `ServerConfig` composing all of the above plus the existing `GameConfig`, so `rating_service.py` depends only on `RatingConfig`, not the whole tree.

Every numeric/string literal introduced by Phases B–E (1200, ±100, K-factor, 60s matchmaking timeout, 20s reconnect window, 20-spectator cap, 4–6 char room codes, PBKDF2 iteration count) must resolve to one of these config objects — never an inline literal, matching the zero-hardcoded-constants rule already honored throughout the existing engine/rules code.

---

## 12. Testing Strategy Matrix

| Layer | Scope | Status | Required for |
|---|---|---|---|
| Unit (domain) | `model/`, `rules/`, `realtime/`, `engine/` | Done (494 passing) | — |
| Unit (application, Phase A) | `GameSession`, `GameService`, `dto` | Done | — |
| Protocol | Envelope encode/decode, malformed-frame rejection | Done (`test_schemas.py`) | — |
| WebSocket integration | connect → join_game → move → broadcast | Done (`test_websocket_gateway.py`) | — |
| **Board synchronization (new, Section 3.4)** | Both clients receive byte-identical snapshots/events | **Not yet added — add now, independent of phase** | all future phases |
| Import boundary | `websocket_gateway.py` never imports model/rules/realtime | Done (`test_import_boundaries.py`) — extend as new server modules are added | B–E |
| Repository contract | Same test suite against in-memory and SQLite implementations | Not yet built | B |
| Auth | Register/login/duplicate-username/hash verification | Not yet built | B |
| Rating | ELO pure functions, exactly-once application | Not yet built | C |
| Matchmaking | ±100 band, timeout, race between match-found and timeout | Not yet built | C |
| Reconnect | Resume-within-window, forfeit-after-window, reconnect-vs-timeout race, **snapshot re-sync on reconnect** | Not yet built | D |
| Rooms/spectators | Capacity, teardown, spectator command rejection | Not yet built | E |
| Logging correlation | `message_id` traceable across a client log line and a server log line | Not yet built | E |

---

## 13. Risk Register (carried forward + new)

| Risk | Phase | Mitigation |
|---|---|---|
| Two boards silently diverge after a reconnect | D | Section 10.3 — full snapshot on rebind, tested per Section 3.4 |
| Duplicate `move_request` from a client retry applies the same move twice | B/C hardening | `message_id` duplicate-window detection in `schemas`/gateway dispatch |
| Rating applied twice for one game | C | In-memory `rating_applied` flag on `GameSession` under its existing lock (Section 9) |
| SQLite write stalls the event loop for all games | B | `asyncio.to_thread`/`aiosqlite` for every DB write, from the first SQLite call, not retrofitted later |
| Spectator accidentally allowed to submit a move | E | Explicit non-player-role check in the gateway, tested |
| Room teardown races with a lingering Phase D reconnect countdown | E | Teardown wins immediately once both player slots are simultaneously empty (adopted from colleague's plan) |
| Config literal drift (e.g. K-factor hardcoded in two places) | B–E | Section 11's config hierarchy, one source per concern |
| A future server module (auth, rooms) accidentally imports `rules`/`model` directly | B–E | Extend `Tests/server/test_import_boundaries.py` for each new module, don't rely on convention alone |

---

## 14. Immediate Next Steps for Claude Code (in priority order)

1. **Add the Board Synchronization test (Section 3.4)** — no new production code required, this is a pure regression-safety addition against the current Phase A implementation. Do this first, before any Phase B code, so every later phase is guarded by it from day one.
2. **Add `protocol_version` to `server/schemas.py::make_envelope`** (Section 6.2) — small, isolated change, best done before Phase B touches the envelope shape further.
3. **Begin Phase B**: `persistence/repositories.py` interfaces → in-memory fake implementation + its unit tests → `application/auth_service.py` against the fake → only then `persistence/sqlite/*` and the real login wiring into `websocket_gateway.py::_handle_connect`.
4. Proceed to Phases C, D, E in the order given in Section 10 — this order matches both source plans' dependency reasoning (matchmaking needs accounts/ratings from B; rooms need session tokens from B for Decision 7's reconnect identification; reconnection is cross-cutting and depends on B, so it is deliberately not first).

Do not implement Phases B–E out of order, and do not skip the Section 3.4 test — it is the cheapest possible insurance against the one failure mode ("the two players see different boards") that would be the most confusing to debug after the fact.
