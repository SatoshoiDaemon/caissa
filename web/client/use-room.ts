"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { io, type Socket } from "socket.io-client";
import { api, errorMessage, type Game, type Move, type Seat } from "./api";

type Ack = { ok: boolean; game_state?: Game; error?: string };
type Packet = { game_state?: Game };
export type Connection = "connecting" | "connected" | "reconnecting" | "offline";

export function useRoom(
  code: string | null, seat: Seat | null, viewing: boolean,
  update: (game: Game) => void, setError: (message: string) => void,
) {
  const socketRef = useRef<Socket | null>(null);
  const [connection, setConnection] = useState<Connection>("connecting");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!code || (!seat && !viewing)) return;
    const socket = io({
      autoConnect: false,
      addTrailingSlash: false,
      transports: ["websocket", "polling"],
      tryAllTransports: true,
      upgrade: false,
      timeout: 5000,
    });
    socketRef.current = socket;
    let active = true;
    let generation = 0;
    let joined = false;
    setConnection("connecting");

    const receive = (packet: Packet) => { if (active && packet.game_state) update(packet.game_state); };
    for (const event of ["room_state", "move_made", "clock_updated", "player_joined",
      "game_ended", "draw_offered", "draw_declined"]) {
      socket.on(event, receive);
    }
    socket.on("player_disconnected", () => {
      // Refresh the snapshot so presence and its deadline come from the server.
      const current = generation;
      const path = seat ? "/games/" + seat.game_id : "/rooms/" + code;
      api<Game | Packet>(path).then((state) => {
        if (!active || generation !== current) return;
        if ("game_id" in state && "board" in state) update(state);
        else receive(state);
      }).catch(() => {});
    });

    socket.on("connect", async () => {
      const current = ++generation;
      setConnection(joined ? "reconnecting" : "connecting");
      try {
        let event = "join_room";
        let payload: Record<string, string>;
        if (seat) {
          payload = { room_code: code, game_id: seat.game_id, player_token: seat.player_token };
        } else {
          event = "spectate_room";
          const spectator = await api<{ spectator_token: string }>("/rooms/" + code + "/spectate", { method: "POST" });
          payload = { room_code: code, spectator_token: spectator.spectator_token };
        }
        if (!active || generation !== current || !socket.connected) return;
        const ack: Ack = await socket.timeout(7000).emitWithAck(event, payload);
        if (!active || generation !== current) return;
        if (!ack.ok) throw new Error(ack.error ?? "request_failed");
        receive(ack);
        joined = true;
        setError("");
        setConnection("connected");
      } catch (err) {
        if (!active || generation !== current) return;
        setError(errorMessage(err));
        setConnection("offline");
      }
    });
    socket.on("disconnect", () => {
      generation++;
      setConnection(socket.active ? "reconnecting" : "offline");
    });
    socket.on("connect_error", () => setConnection(socket.active ? "reconnecting" : "offline"));
    socket.connect();
    return () => {
      active = false;
      socket.removeAllListeners();
      socket.disconnect();
      socketRef.current = null;
    };
  }, [code, seat, viewing, attempt, update, setError]);

  async function send(event: string, move?: Move) {
    const socket = socketRef.current;
    if (!socket?.connected || connection !== "connected" || !seat) throw new Error("request_failed");
    const ack: Ack = await socket.timeout(7000).emitWithAck(event, {
      room_code: code, game_id: seat.game_id, player_token: seat.player_token,
      event_id: crypto.randomUUID(), ...(move ? { move } : {}),
    });
    if (!ack.ok) throw new Error(ack.error ?? "request_failed");
    if (ack.game_state) update(ack.game_state);
  }

  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  return { connection, send, retry };
}
