export type Color = "white" | "black";
export type Promotion = "q" | "r" | "b" | "n";
export type Piece = { type: Promotion | "p" | "k"; color: Color };
export type BoardState = (Piece | null)[][];
export type Move = { from: string; to: string; promotion?: Promotion; san?: string };
export type User = {
  username: string; bio: string; status: string; status_message: string;
  status_emoji: string | null; profile_image_url: string | null; timezone: string;
};
export type Game = {
  game_id: string; mode: string; board: BoardState; current_player: Color;
  status: string; winner: Color | null; version: number; in_check: boolean;
  white_player: string | null; black_player: string | null;
  white_connected: boolean; black_connected: boolean;
  white_reconnect_deadline_at: string | null; black_reconnect_deadline_at: string | null;
  white_time_remaining_ms: number | null; black_time_remaining_ms: number | null;
  clock_version: number; active_clock_color: Color | null;
  move_history: Move[]; draw_offer: { offered_by: Color | null; version: number };
};
export type Room = {
  room_code: string; game_id: string; name: string; mode: string;
  status: string; access_mode: string; game_state?: Game;
};
export type Seat = {
  game_id: string; room_code: string | null; player_color: Color;
  player_token: string; black_player_token?: string;
};
export type Entry = Seat & { game_state: Game };
export type Result = { game_id: string; result: string; status: string; mode: string; completed_at: string };
export type Stats = Record<"overall" | "week" | "month", {total: number; wins: number; losses: number; draws: number}>;

export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

export async function api<T>(path: string, options: {
  method?: string; body?: unknown; token?: string; signal?: AbortSignal;
} = {}): Promise<T> {
  const { method, body, token, signal } = options;
  const response = await fetch("/api/v1" + path, {
    method, signal, cache: "no-store", credentials: "same-origin",
    headers: {
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: "Bearer " + token } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok || data === null) {
    throw new ApiError(data?.error ?? "request_failed", response.status);
  }
  return data as T;
}

const seatKey = (id: string) => "caissa:seat:v1:" + id;

export function saveSeat(entry: Entry, id: string) {
  const { game_id, room_code, player_color, player_token, black_player_token } = entry;
  sessionStorage.setItem(seatKey(id), JSON.stringify({
    game_id, room_code, player_color, player_token, black_player_token,
  }));
}

export function readSeat(id: string): Seat | null {
  try { return JSON.parse(sessionStorage.getItem(seatKey(id)) ?? "null"); }
  catch { return null; }
}

export const errorMessage = (error: unknown) => error instanceof Error ? error.message : "request_failed";
