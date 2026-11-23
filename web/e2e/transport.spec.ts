import { test, expect, type APIRequestContext } from "@playwright/test";
import { io } from "socket.io-client";

test("proxy preserves cookies, websocket moves, reconnect and persisted result", async ({ playwright, baseURL }) => {
  const white = await playwright.request.newContext({ baseURL });
  const black = await playwright.request.newContext({ baseURL });
  const suffix = Date.now().toString(36);
  const whiteName = "host_" + suffix;
  const blackName = "guest_" + suffix;

  async function register(client: APIRequestContext, username: string) {
    const response = await client.post("/api/v1/auth/register", {
      data: { username, password: "a-test-password-for-caissa" },
    });
    expect(response.status()).toBe(201);
    const session = (await client.storageState()).cookies.find(({ name }) => name === "caissa_session");
    expect(session?.httpOnly).toBe(true);
    expect((await (await client.get("/api/v1/auth/me")).json()).user.username).toBe(username);
  }

  const connect = () => io(baseURL!, {
    autoConnect: false, addTrailingSlash: false, timeout: 6000, transports: ["websocket"], reconnection: false,
    extraHeaders: { Origin: baseURL! },
  });
  const first = connect();
  const second = connect();
  const restored = connect();

  async function start(socket: typeof first, credentials: object) {
    await new Promise<void>((resolve, reject) => {
      socket.once("connect", resolve);
      socket.once("connect_error", reject);
      socket.connect();
    });
    expect(await socket.timeout(5000).emitWithAck("join_room", credentials)).toEqual({ ok: true });
  }

  try {
    await register(white, whiteName);
    await register(black, blackName);
    const creation = await white.post("/api/v1/rooms", {
      data: { name: "Classical test", mode: "classical", access_mode: "code_only" },
    });
    expect(creation.status()).toBe(201);
    const created = await creation.json();
    const path = "/api/v1/games/" + created.game_id;
    const join = await black.post("/api/v1/rooms/" + created.room_code + "/join", { data: { player_name: blackName } });
    expect(join.ok()).toBe(true);
    const joined = await join.json();
    const whiteSeat = { game_id: created.game_id, room_code: created.room_code, player_token: created.player_token };
    const blackSeat = { ...whiteSeat, player_token: joined.player_token };

    await start(first, whiteSeat);
    await start(second, blackSeat);
    const initial = await (await white.get(path)).json();
    expect(initial.active_clock_color).toBe("white");
    expect(initial.black_time_remaining_ms).toBe(1_800_000);
    const rejected = await second.timeout(5000).emitWithAck("make_move", { ...blackSeat, move: { from: "e7", to: "e5" } });
    expect(rejected.ok).toBe(false);

    async function move(socket: typeof first, peer: typeof first, seat: object, from: string, to: string, san: string) {
      const broadcast = new Promise<{game_state: {last_move_san: string}}>((resolve) => peer.once("move_made", resolve));
      const ack = await socket.timeout(5000).emitWithAck("make_move", {
        ...seat, move: { from, to }, event_id: crypto.randomUUID(),
      });
      expect(ack.ok).toBe(true);
      expect(ack.game_state.last_move_san).toBe(san);
      expect((await broadcast).game_state.last_move_san).toBe(san);
      return ack.game_state;
    }

    await move(first, second, whiteSeat, "f2", "f3", "f3");
    const disconnected = new Promise<void>((resolve) => first.once("player_disconnected", resolve));
    second.disconnect();
    await disconnected;
    await start(restored, blackSeat);
    const resumed = await (await black.get(path)).json();
    expect(resumed.last_move_san).toBe("f3");
    expect(resumed.black_connected).toBe(true);
    await move(restored, first, blackSeat, "e7", "e5", "e5");
    await move(first, restored, whiteSeat, "g2", "g4", "g4");
    const ended = await move(restored, first, blackSeat, "d8", "h4", "Qh4#");
    expect(ended.status).toBe("checkmate");
    expect(ended.winner).toBe("black");

    const review = await (await white.get(path + "/replay")).json();
    expect(review.positions).toHaveLength(5);
    const history = await (await black.get("/api/v1/users/me/games")).json();
    expect(history.games).toEqual([expect.objectContaining({ game_id: created.game_id, result: "win" })]);
  } finally {
    first.disconnect();
    second.disconnect();
    restored.disconnect();
    await Promise.all([white.dispose(), black.dispose()]);
  }
});
