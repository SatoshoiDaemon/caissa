---
target: src/frontend/templates/index.html
total_score: 20
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 4
target_identity: "file:/home/cyberbot/Downloads/Portifólio/xadrez/xadrez_web/src/frontend/templates/index.html"
target_fingerprint: "sha256:2071bc5cc2c6abf5ffcf0b61c54f23260d9e1cc33f27b74bfd88a3b8326f6d98"
target_path: /home/cyberbot/Downloads/Portifólio/xadrez/xadrez_web/src/frontend/templates/index.html
timestamp: 2026-10-06T01-51-43Z
slug: src-frontend-templates-index-html
---
# Caissa frontend critique

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|---|---:|---|
| 1 | Visibility of System Status | 2/4 | State depends on alerts, generic copy, and inconsistent visual changes. |
| 2 | Match System / Real World | 3/4 | Rooms, players, spectators, clocks, and promotion are recognizable. |
| 3 | User Control and Freedom | 2/4 | Cancel exists, but dialogs lack consistent Escape and focus behavior. |
| 4 | Consistency and Standards | 2/4 | Old and new visual styles and separate local/online/spectator flows are mixed. |
| 5 | Error Prevention | 2/4 | Server validation exists, but the UI exposes fields the server may ignore or reject. |
| 6 | Recognition Rather Than Recall | 2/4 | Labels are clear in isolation, but context and persistent state are weak. |
| 7 | Flexibility and Efficiency | 2/4 | No keyboard shortcuts, quick navigation, or exposed room continuity. |
| 8 | Aesthetic and Minimalist Design | 2/4 | Home accumulates authentication, rooms, creation, joining, and discovery in a narrow composition. |
| 9 | Error Recovery | 2/4 | `alert()` interrupts flow and provides little recovery guidance. |
| 10 | Help and Documentation | 1/4 | No contextual help for codes, modes, spectators, clocks, or recovery. |
| **Total** |  | **20/40** | **Functional foundation, but prototype-level finish and high cognitive load.** |

## Design Specificity Verdict

Caissa has distinctive functional elements—public rooms, spectator mode, server-authoritative clocks, promotion, and recovery codes—but its presentation still resembles a generic web-game prototype: purple gradient, default blue buttons, translucent cards, and Unicode chess pieces. The biggest opportunity is to make the interface express its core idea: a casual, trustworthy, live arena for real-time games.

The detector returned zero deterministic findings, but with incomplete coverage because it could not resolve `css/style.css` relative to the template. This prevented complete color and custom-property analysis. Browser visualization was also unavailable because Flask is not installed in the environment and the embedded browser blocked the local visual server with `ERR_BLOCKED_BY_CLIENT`; no reliable overlay is available.

## Overall Impression

The product has a clear functional foundation, but the interface has grown by adding dialogs and controls without one visual architecture. The home feels like an older menu with account, rooms, and spectator features attached; the game view feels like a different product. The largest gain would come from one shared Caissa arena shell across lobby, room, and game.

## What's Working

- Public rooms, spectating, clocks, player status, and promotion communicate real product capabilities.
- The promotion dialog has dialog semantics, a labelled title, four named choices, and partial keyboard handling.
- The room list uses `aria-live`, escapes content before inserting HTML, and offers explicit join and spectate actions.

## Priority Issues

### [P1] The home lacks product hierarchy

Authentication, local play, online play, and public-room discovery compete for the same space. Make the home an explicit lobby with one primary create-game action, a secondary local action, and a room section with filters and states. Move account identity into a quieter area.

### [P1] Game screen and home have different visual languages

The white home and purple translucent game screen feel like separate products. Establish one surface system for lobby, board, and dialogs; make the board the visual focus and use semantic tokens for active, disconnected, draw-offer, check, and finished states.

### [P1] Critical feedback relies on `alert()`

Login, room errors, disconnection, draw offers, reconnection, and server errors interrupt the experience. Create a persistent toast/status system with `aria-live`, severity, loading states, and recovery actions; use contextual confirmation for draw and resign.

### [P1] Spectator and reconnection loops are under-communicated

The backend supports these states, but the frontend mostly shows a small banner. Add connection status, a persistent spectator state, an event panel, and explicit reconnecting, reconnected, abandoned, and expired-room states. Remove or replace mutation controls in spectator mode.

### [P2] Keyboard accessibility and dialogs are incomplete

Add explicit labels, strong `:focus-visible`, focus trapping, Escape, focus return, `aria-describedby`, invalid states, and keyboard operation for the board. Do not rely on placeholders or clicks alone.

### [P2] Responsive layout does not preserve priority

At smaller widths, controls become a horizontal strip or a long vertical stack. Use mobile-first priority: board first, compact clocks, primary action group, and history in a drawer or accordion. Test 320px, 375px, 768px, and landscape.

## Persona Red Flags

- **Alex, power user:** no keyboard shortcuts or navigable notation; alerts obscure whether an action was accepted.
- **Jordan, first-timer:** encounters multiple competing decisions before understanding the product; local, online, create-room, and join-room paths are fragmented.
- **Sam, mobile spectator:** player and spectator controls look similar; the small read-only banner does not explain reconnection, expiry, timeout, or end states.

## Minor Observations

- The home promise is generic despite a much stronger technical differentiator.
- Dark room cards inside the light menu may inherit dark text for some content and need a contrast pass.
- “Desfazer” is exposed although backend undo is unavailable, creating a false affordance.
- Time and increment fields are visible even though server presets are authoritative.
- A 500ms status interval runs even without an active game.
- Profile UI does not expose bio, stats, or history despite backend support.
- Unicode pieces and emoji can vary across platforms.
- Socket.IO is loaded from a CDN, adding an external dependency to local operation.

## Questions to Consider

- What if the home were an intentional lobby instead of a menu with attached dialogs?
- Could the game state and connection state be as visually important as the board itself?
- What would a confident mobile spectator experience look like if all mutation controls disappeared entirely?
