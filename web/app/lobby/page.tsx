"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { api, errorMessage, saveSeat, type Entry, type Room } from "../../client/api";
import { ImportPgn } from "../../components/replay";
import { Feedback, useApp } from "../../components/shell";

export default function Lobby() {
  const { t, user, loading } = useApp();
  const router = useRouter();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [error, setError] = useState("");
  const [listError, setListError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [listed, setListed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    api<{rooms: Room[]}>("/rooms?limit=20", { signal: controller.signal })
      .then(({ rooms }) => { setRooms(rooms); setListError(""); setListed(true); })
      .catch((err) => { if (!controller.signal.aborted) setListError(errorMessage(err)); });
    return () => controller.abort();
  }, [refresh]);

  async function create(event: FormEvent<HTMLFormElement>, local: boolean) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const fields = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const entry = await api<Entry>(local ? "/games" : "/rooms", {
        method: "POST", body: local ? { ...fields, mode: "local" } : fields,
      });
      const id = entry.room_code ?? entry.game_id;
      saveSeat(entry, id);
      router.push((local ? "/local/" : "/room/") + id);
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }

  return <div className="grid gap-6">
    <h1>Lobby</h1>
    <Feedback error={error} />
    <div className="grid gap-4 md:grid-cols-3">
      <section className="panel grid content-start gap-3">
        <h2>{t("Criar sala", "Create room")}</h2>
        {user ? <form className="grid gap-3" onSubmit={(event) => create(event, false)}>
          <label>{t("Nome da sala", "Room name")}<input name="name" required minLength={3} maxLength={48} /></label>
          <label>{t("Relógio", "Time control")}<select name="mode" defaultValue="blitz">
            <option value="bullet">Bullet · 1 min</option><option value="blitz">Blitz · 5 min</option>
            <option value="rapid">{t("Rápido", "Rapid")} · 10 min</option>
            <option value="classical">{t("Clássico", "Classical")} · 30 min</option>
          </select></label>
          <label>{t("Visibilidade", "Visibility")}<select name="access_mode">
            <option value="public">{t("Pública", "Public")}</option>
            <option value="code_only">{t("Somente por código", "Invite code only")}</option>
          </select></label>
          <button disabled={busy} className="primary">{t("Criar sala", "Create room")}</button>
        </form> : loading ? <p>{t("Verificando sessão…", "Checking session…")}</p>
          : <Link href="/login">{t("Entre para criar uma sala", "Sign in to create a room")}</Link>}
      </section>
      <section className="panel grid content-start gap-3">
        <h2>{t("Entrar por código", "Join by code")}</h2>
        <form className="grid gap-3" onSubmit={(event) => {
          event.preventDefault();
          const code = String(new FormData(event.currentTarget).get("code")).trim().toUpperCase();
          router.push("/room/" + encodeURIComponent(code));
        }}>
          <label>{t("Código da sala", "Room code")}<input className="code uppercase" name="code" required pattern="[a-zA-Z0-9]{8}" maxLength={8} /></label>
          <button>{t("Abrir sala", "Open room")}</button>
        </form>
      </section>
      <section className="panel grid content-start gap-3">
        <h2>{t("Jogar no mesmo dispositivo", "Play on this device")}</h2>
        <form className="grid gap-3" onSubmit={(event) => create(event, true)}>
          <label>{t("Brancas", "White")}<input name="player_name" defaultValue={user?.username} required maxLength={32} /></label>
          <label>{t("Pretas", "Black")}<input name="black_player" required maxLength={32} /></label>
          <button disabled={busy}>{t("Iniciar partida local", "Start local game")}</button>
        </form>
      </section>
    </div>
    <section className="panel grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2>{t("Salas públicas", "Public rooms")}</h2>
        <button onClick={() => setRefresh((value) => value + 1)}>{t("Atualizar", "Refresh")}</button>
      </div>
      <Feedback error={listError} />
      {rooms.length ? <ul className="grid divide-y divide-slate-700">
        {rooms.map((room) => <li key={room.game_id} className="flex flex-wrap justify-between gap-2 py-3">
          <Link href={"/room/" + room.room_code}>{room.name}</Link>
          <span className="muted">{room.mode} · {room.status === "waiting"
            ? t("Vaga disponível", "Seat open") : t("Em jogo", "In progress")}</span>
        </li>)}
      </ul> : !listError && <p className="muted">{listed ? t("Nenhuma sala disponível.", "No rooms available.")
        : t("Carregando salas…", "Loading rooms…")}</p>}
    </section>
    <ImportPgn />
  </div>;
}
