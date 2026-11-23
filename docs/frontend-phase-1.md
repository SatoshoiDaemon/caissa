# Caissa frontend migration

## Baseline

The audit used commit `21f6ecd` before code edits. The original suite reported 64 passed and 4 skipped. The skipped tests require real MongoDB and Redis services.

Flask registers the API blueprints and the original HTML routes in `src/backend/app/__init__.py`. The original frontend uses templates and browser scripts under `src/frontend`. `chess_logic` owns classical rules and PGN, `GameService` owns game transitions and clocks, `AccountService` owns accounts and results, and `RoomService` owns discovery and spectator credentials. MongoDB holds durable state and move history. Redis coordinates locks, presence, and messages. The browser consumes snapshots and submits commands.

## Integration contracts

All REST paths below start with `/api/v1`.

| Contract | Methods and paths | Notes |
| --- | --- | --- |
| Session | POST `/auth/register`, `/auth/login`, `/auth/logout`; GET `/auth/me` | Flask issues the opaque HttpOnly session cookie. Registration returns one-time recovery codes. |
| Account security | POST `/auth/recovery`, `/auth/password`, `/auth/recovery-codes` | Password changes revoke existing sessions. Recovery does not sign the account in. |
| Profiles | GET `/users/{username}`, `/users/{username}/stats`, `/users/{username}/games`; PATCH `/users/me/profile`; GET `/users/me/stats`, `/users/me/games` | Public profile, per-period stats and completed results. |
| Rooms | GET and POST `/rooms`; GET `/rooms/{code}`; POST `/rooms/{code}/join`, `/rooms/{code}/spectate` | Creation requires an account. An invited guest can claim the second seat by supplying a name. Spectator access is public rooms only. |
| Local game | POST `/games` with `mode: local` | Returns one token per color. The original endpoint also accepts `mode: online`. |
| State and moves | GET `/games/{id}`, `/games/{id}/moves/{square}`; POST `/games/{id}/moves`, `/games/{id}/reconnect` | Mutations use the game bearer token. The new online client rejoins using Socket.IO so presence is registered to its socket. |
| Endings and draws | POST `/games/{id}/resign` and `/games/{id}/draw/{offer,accept,decline}` | The legacy `POST /rooms/{code}/draw` responds with a status marker. Match commands use the game contract. |
| Review | GET `/games/{id}/replay`, `/games/{id}/pgn`; POST `/games/import` | Replay includes persisted moves and the server-generated board at every position. An active game returns 409 for replay. |

| Socket.IO contract | Events |
| --- | --- |
| Join and subscribe | `join_room` takes room code, game ID and player token. `spectate_room` takes room code and a spectator token. Both return an acknowledgement. |
| Commands | `make_move`, `resign_game`, `offer_draw`, `accept_draw`, `decline_draw` take the seat credentials and an event ID. Moves also carry origin, destination and optional promotion. |
| Snapshots | `room_joined`, `room_state`, `player_joined`, `move_made`, `clock_updated`, `draw_offered`, `draw_declined`, `game_ended`. Terminal moves are also visible through the status in `move_made`. |
| Presence and errors | `player_disconnected`, `player_reconnected`, `spectator_joined`, `server_error`. The existing player grace period is 60 seconds. Reconnect with the same seat token. A spectator must obtain a fresh token following disconnect. |

The Next app proxies REST and Socket.IO to Flask. The browser uses the same origin for forms, cookies and the socket transport. Game seat credentials are kept in tab session storage independent of the account cookie. Reloading the same tab restores the seat, and closing it can discard the token. Invite links contain only the room code. The React board renders server state and uses the server move list for move hints. The arena renders clock values received from the server.

Next and Flask can run side by side. In production, set `CAISSA_BACKEND_URL` when building and running Next, add the public frontend origin to Flask's `ALLOWED_ORIGINS`, and route `/socket.io/` with WebSocket upgrades and HTTP polling support. Use HTTPS for production cookies. The Flask frontend remains available for gradual migration.

## Extension points

| Capability | Proposed interface and location |
| --- | --- |
| Rules engine | Introduce an engine protocol at the boundary between `GameService` and `ChessGame` once another ruleset needs it: `initial_state(definition)`, `legal_actions(state, actor)`, `apply(state, action)` and `outcome(state)`. Keep clocks, persistence, authorization and event ordering in the service. |
| Custom pieces and attacks | Give pieces stable type IDs. Describe movement and attack separately. Use typed actions and structured effects so a single action can remove several pieces or affect a square other than its destination. The client renders actions and hints supplied by the engine. |
| Variant versions | Pin a variant ID and immutable version to a created game and its replay. Read historical games as classical by default. Keep FEN, SAN and PGN for classical games and introduce a versioned representation as the next ruleset requires. |
| Bots | Give a strategy a read-only snapshot, legal actions, a deadline and an optional seed. Submit the selected action through the authorized game command path and recheck the state version before applying it. |
| Matchmaking | Queue by variant and version, time control and skill range. Reserve two seats atomically, create games through the existing services and keep queue membership separate from the outcome and rating records. |
| Visual editor | Edit a draft declarative ruleset and preview it with the same server validator. Publish immutable versions from validated drafts. Store display assets apart from rule definitions. |

## Verification

Install Python development dependencies with `python -m pip install -e '.[dev]'`. In `web`, use `npm ci`, `npm run build`, and `npm run check`. Run `npx playwright install chromium` before `npm test`, or set `CAISSA_CHROMIUM_PATH` to a compatible system Chromium. Playwright runs a real Next server and Flask Socket.IO server against isolated MongoDB and Redis test doubles. Use the Python infrastructure suite with real services to separately validate database and Redis behavior.
