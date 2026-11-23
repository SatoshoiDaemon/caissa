"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, errorMessage, readSeat, saveSeat, type Color, type Entry, type Game, type Move, type Room, type Seat } from "../client/api";
import { useRoom } from "../client/use-room";
import { Arena } from "./arena";
import { Feedback, useApp } from "./shell";

export function GamePage({ id, local = false }: { id: string; local?: boolean }) {
  const { t, user } = useApp();
  const [room, setRoom] = useState<Room>();
  const [game, setGame] = useState<Game>();
  const [seat, setSeat] = useState<Seat | null>(null);
  const [viewing, setViewing] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const update = useCallback((next: Game) => {
    setGame((current) => {
      if (!current) return next;
      if (next.game_id !== current.game_id || next.version < current.version) return current;
      if (next.version === current.version &&
          (next.clock_version < current.clock_version || (current.black_player && !next.black_player))) return current;
      return next;
    });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setSeat(readSeat(id));
    if (local) {
      api<Game>("/games/" + id, { signal: controller.signal }).then(update)
        .catch((err) => { if (!controller.signal.aborted) setError(errorMessage(err)); });
    } else {
      api<Room>("/rooms/" + id, { signal: controller.signal }).then((value) => {
        setRoom(value);
        if (value.game_state) update(value.game_state);
      }).catch((err) => { if (!controller.signal.aborted) setError(errorMessage(err)); });
    }
    return () => controller.abort();
  }, [id, local, update]);
  const { connection, send, retry } = useRoom(local ? null : id, seat, viewing, update, setError);

  async function join(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const entry = await api<Entry>("/rooms/" + id + "/join", {
        method: "POST", body: Object.fromEntries(new FormData(event.currentTarget)),
      });
      saveSeat(entry, id);
      update(entry.game_state);
      setSeat(readSeat(id));
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }

  async function play(event: string, move?: Move, color?: Color) {
    if (!local) return send(event, move);
    const token = color === "black" ? seat?.black_player_token : seat?.player_token;
    if (!token) throw new Error("invalid player token");
    const path = "/games/" + id + (event === "make_move" ? "/moves" : "/resign");
    update(await api<Game>(path, { method: "POST", token, body: { ...move, event_id: crypto.randomUUID() } }));
  }

  const connectionText = {
    connecting: t("Conectando…", "Connecting…"), connected: t("Conectado", "Connected"),
    reconnecting: t("Reconectando…", "Reconnecting…"), offline: t("Sem conexão", "Offline"),
  };
  return <div className="grid gap-5">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div className="grid gap-2">
        <Link href="/lobby">← Lobby</Link>
        <h1>{local ? t("Partida local", "Local game") : room?.name ?? t("Sala", "Room")}</h1>
        {!local && <span className="code muted">{id}{viewing && " · " + t("Espectador", "Spectator")}</span>}
      </div>
      {!local && <button onClick={async () => {
        try { await navigator.clipboard.writeText(location.href); setCopied(true); }
        catch { setError("request_failed"); }
      }}>{copied ? t("Link copiado", "Link copied") : t("Copiar convite", "Copy invite")}</button>}
    </div>
    {!local && (seat || viewing) && <div className="flex flex-wrap items-center gap-3">
      <p role="status">{connectionText[connection]}</p>
      {(connection === "offline" || connection === "reconnecting") &&
        <button onClick={retry}>{t("Tentar novamente", "Try again")}</button>}
    </div>}
    <Feedback error={error} />
    {!local && room && !seat && !viewing && <section className="panel flex flex-wrap items-end gap-4">
      {room.status === "waiting" && <form className="flex flex-wrap items-end gap-3" onSubmit={join}>
        <label>{t("Seu nome", "Your name")}<input name="player_name" required maxLength={32} defaultValue={user?.username} /></label>
        <button disabled={busy} className="primary">{t("Entrar na sala", "Join room")}</button>
      </form>}
      {room.access_mode === "public" && room.status !== "finished" &&
        <button onClick={() => { setError(""); setViewing(true); }}>{t("Assistir", "Spectate")}</button>}
    </section>}
    {local && game?.status === "active" && !seat && <Feedback error="invalid player token" />}
    {game ? <Arena game={game} color={seat?.player_color} local={local}
      playable={!!seat && (local || connection === "connected")} send={play} />
      : !error && <p role="status">{t("Carregando partida…", "Loading game…")}</p>}
  </div>;
}
