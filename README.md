# Caissa

Official repository: [github.com/SatoshoiDaemon/Caissa](https://github.com/SatoshoiDaemon/Caissa)

Caissa is a local real-time multiplayer chess prototype. Its purpose is to demonstrate server-authoritative state management, authenticated WebSocket events, concurrent game sessions, Redis coordination, and MongoDB persistence.

It is intentionally not designed to compete with chess platforms such as chess.com. The project focuses on room membership, player authorization, ordered state transitions, reconnection, persistence, and conflict handling.

## Architecture

```text
Browser ── REST/WebSocket ── Flask + Flask-SocketIO
                              │
                 ┌────────────┴────────────┐
                 │                         │
              MongoDB                    Redis
        durable game state       locks, rate limits,
        and move history          presence and events
```

- MongoDB is the source of truth for games, rooms, players, state versions, and move history.
- Redis coordinates only short-lived locks, rate limiting, presence, pub/sub, and Socket.IO coordination. It is never the source of truth for a game.
- The browser is never trusted to provide its own color, room membership, or turn authority.
- Every online player receives an opaque per-game token. Only its SHA-256 hash is stored.
- Moves use a per-game Redis lock and optimistic MongoDB versioning.
- Reconnecting with the original token restores the persisted FEN, turn, status, version, history, and clock metadata.
- A duplicate connection for the same player replaces the previous transient Socket.IO presence without creating another player.
- Public rooms require an authenticated account, while code-only rooms remain unlisted and can be shared privately.
- Anonymous spectators receive short-lived read-only tokens; spectator connections can observe state and clocks but cannot mutate games.
- Competitive room clocks are calculated by the server, persisted in MongoDB, and end games by timeout before accepting a late move.
- Draw offers, resignation, disconnection, reconnection, abandonment, and timeout are persisted state transitions with a 60-second reconnection grace period.
- SQLite is not part of the runtime. The current database starts empty by design; old SQLite data is disposable for this migration.

The backend lives under `src/backend` and the browser application under `src/frontend`. Python modules and JSON fields use `snake_case`; JavaScript functions use `camelCase`; Socket.IO event names use `snake_case`; API routes are versioned under `/api/v1`.

## Local setup

Requirements: Python 3.10+, Docker Compose, and a browser.

```bash
cp .env.example .env
# Replace SECRET_KEY with a long random value
docker compose up -d
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
PYTHONPATH=src python -m backend.run
```

Open http://127.0.0.1:5000.

The Compose file runs only MongoDB and Redis. The application itself runs directly from Python so that the backend remains easy to inspect and debug.

## API

```text
POST /api/v1/games
GET  /api/v1/games/{game_id}
POST /api/v1/games/{game_id}/reconnect
POST /api/v1/games/{game_id}/moves
GET  /api/v1/games/{game_id}/moves/{position}

GET  /api/v1/rooms
POST /api/v1/rooms
GET  /api/v1/rooms/{room_code}
POST /api/v1/rooms/{room_code}/join
POST /api/v1/rooms/{room_code}/spectate

POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/password
POST /api/v1/auth/recovery
POST /api/v1/auth/recovery-codes

GET   /api/v1/users/{username}
GET   /api/v1/users/{username}/stats
GET   /api/v1/users/{username}/games
PATCH /api/v1/users/me/profile
GET   /api/v1/users/me/stats
GET   /api/v1/users/me/games
```

Mutation requests require `Authorization: Bearer <player_token>`. WebSocket clients use the same token in `join_room`, `make_move`, `offer_draw`, `accept_draw`, and `resign_game` events.

The home page lists non-expired public rooms with their creator, opponent, mode, status, clocks, and spectator count. A spectator first calls `/spectate`, then connects with the returned temporary token using the `spectate_room` Socket.IO event. Spectators receive `room_state`, `move_made`, `clock_updated`, and `game_ended`, but all mutation events are rejected server-side.

## Browser routes and clocks

The single-page frontend supports direct navigation and refresh at `/`, `/home`, `/login`, `/u/<username>`, and `/room/<room_code>`. Flask serves the application shell only for these explicit routes; `/api/v1/...`, static files, and unknown paths retain their normal behavior.

Room clocks use server-authoritative presets: `bullet` (1 minute), `blitz` (5 minutes), `rapid` (10 minutes), and `classical` (30 minutes). The browser renders `*_time_remaining_ms` values returned by the server and never decrements or calculates the clock locally.

Player refresh/reconnection uses the temporary per-game token held in `sessionStorage` and `POST /api/v1/games/<game_id>/reconnect`. A room without a valid player token is opened as a read-only spectator only when the room policy permits it; code-only rooms are not silently downgraded.

Competitive clocks use server-side mode presets: bullet (60 seconds), blitz (5 minutes), rapid (10 minutes), and classical (30 minutes). MongoDB persists `white_time_remaining_ms`, `black_time_remaining_ms`, `active_clock_color`, `clock_started_at`, `clock_increment_ms`, and `clock_version`. The browser renders received values and never decrements the clock locally.

The realtime lifecycle uses `offer_draw`, `accept_draw`, `decline_draw`, `resign_game`, `player_disconnected`, `player_reconnected`, and `game_ended`. Mutating events may include an `event_id`; repeated IDs return the persisted result without applying a second transition.

Account authentication uses an opaque `caissa_session` HttpOnly cookie. Passwords and recovery codes are hashed with Argon2id. Recovery codes are generated once, shown once, and can be downloaded as `caissa-recovery-codes.txt`. There is no email-based recovery.

## Quality commands

```bash
make test
make lint
make security
make run
```

Integration tests that require real MongoDB and Redis are marked with `integration`.

Because Caissa has no production data yet, the initial schema is intentionally destructive. To reset all game, account, session, recovery-code, and statistics collections:

```bash
make reset-db
```

The command requires the explicit `RESET_CONFIRM=CAISSA` guard and performs no migration.

## Scope

This project is a portfolio prototype for real-time systems engineering. It prioritizes authorization, concurrency, state persistence, clocks, public room discovery, spectator access, and event delivery over rankings, matchmaking, AI, or horizontal production deployment.
