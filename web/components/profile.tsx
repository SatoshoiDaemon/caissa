"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { api, errorMessage, type Result, type Stats, type User } from "../client/api";
import { resultLabel } from "./arena";
import { RecoveryCodes } from "./recovery-codes";
import { Feedback, useApp } from "./shell";

export function Profile({ username }: { username: string }) {
  const { lang, t, user, setUser } = useApp();
  const [profile, setProfile] = useState<User>();
  const [stats, setStats] = useState<Stats>();
  const [games, setGames] = useState<Result[]>([]);
  const [codes, setCodes] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const own = user?.username === profile?.username && !!user;

  useEffect(() => {
    const controller = new AbortController();
    const base = "/users/" + encodeURIComponent(username);
    const opts = { signal: controller.signal };
    Promise.all([
      api<{user: User}>(base, opts), api<Stats>(base + "/stats", opts),
      api<{games: Result[]}>(base + "/games", opts),
    ]).then(([profile, stats, history]) => {
      setProfile(profile.user);
      setStats(stats);
      setGames(history.games);
    }).catch((err) => { if (!controller.signal.aborted) setError(errorMessage(err)); });
    return () => controller.abort();
  }, [username]);

  async function save(event: FormEvent<HTMLFormElement>, action: "profile" | "password" | "recovery") {
    event.preventDefault();
    const form = event.currentTarget;
    const body = Object.fromEntries(new FormData(form));
    setError("");
    setFeedback("");
    setBusy(true);
    try {
      if (action === "profile") {
        const { user } = await api<{user: User}>("/users/me/profile", { method: "PATCH", body });
        setProfile(user);
        setUser(user);
        setFeedback(t("Perfil atualizado.", "Profile updated."));
      } else if (action === "password") {
        await api("/auth/password", { method: "POST", body });
        setUser(null);
        setCodes([]);
        setFeedback(t("Senha alterada. Entre novamente.", "Password changed. Sign in again."));
      } else {
        const response = await api<{ recovery_codes: string[] }>("/auth/recovery-codes", { method: "POST", body });
        setCodes(response.recovery_codes);
      }
      if (action !== "profile") form.reset();
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }

  return <div className="grid gap-4">
    <h1>{profile?.username ?? username}</h1>
    <Feedback error={error} />
    {feedback && <p role="status">{feedback}</p>}
    {profile && <>
      <section className="panel flex items-center gap-4">
        {profile.profile_image_url && <img src={profile.profile_image_url} alt="" width="64" height="64" className="rounded-full" />}
        <div><p>{profile.status}</p><p className="muted whitespace-pre-wrap">{profile.bio || t("Sem biografia.", "No bio yet.")}</p></div>
      </section>
      <section className="panel grid gap-3">
        <h2>{t("Estatísticas", "Statistics")}</h2>
        {stats && (["overall", "week", "month"] as const).map((period, index) => <div key={period}>
          <strong>{[t("Total", "All time"), t("Semana", "This week"), t("Mês", "This month")][index]}</strong>
          <p className="muted">{stats[period].wins} {t("vitórias", "wins")} · {stats[period].losses} {t("derrotas", "losses")} · {stats[period].draws} {t("empates", "draws")}</p>
        </div>)}
      </section>
      <section className="panel grid gap-3">
        <h2>{t("Histórico de partidas", "Match history")}</h2>
        {games.length ? <ul className="grid divide-y divide-slate-700">{games.map((game) => <li key={game.game_id} className="flex flex-wrap justify-between gap-2 py-2">
          <Link href={"/games/" + game.game_id}>{resultLabel(game.status, t)} · {game.mode}</Link>
          <span>{game.result === "win" ? t("Vitória", "Win") : game.result === "loss" ? t("Derrota", "Loss") : t("Empate", "Draw")}</span>
          <time dateTime={game.completed_at}>{new Date(game.completed_at).toLocaleDateString(lang)}</time>
        </li>)}</ul> : <p className="muted">{t("Nenhuma partida concluída.", "No completed games.")}</p>}
      </section>
      {own && <>
        <details className="panel">
          <summary className="cursor-pointer">{t("Editar perfil", "Edit profile")}</summary>
          <form className="mt-4 grid gap-3" onSubmit={(event) => save(event, "profile")}>
            <label>{t("Bio", "Bio")}<textarea name="bio" maxLength={500} defaultValue={profile.bio} /></label>
            <label>{t("Emoji de status", "Status emoji")}<input name="status_emoji" defaultValue={profile.status_emoji ?? ""} /></label>
            <label>{t("Mensagem de status", "Status message")}<input name="status_message" maxLength={64} defaultValue={profile.status_message} /></label>
            <label>{t("URL da imagem", "Image URL")}<input name="profile_image_url" type="url" defaultValue={profile.profile_image_url ?? ""} /></label>
            <label>{t("Fuso horário (IANA)", "Time zone (IANA)")}<input name="timezone" defaultValue={profile.timezone} required /></label>
            <button disabled={busy}>{t("Salvar perfil", "Save profile")}</button>
          </form>
        </details>
        <details className="panel">
          <summary className="cursor-pointer">{t("Segurança da conta", "Account security")}</summary>
          <div className="mt-4 grid gap-5 md:grid-cols-2">
            <form className="grid content-start gap-3" onSubmit={(event) => save(event, "password")}>
              <label>{t("Senha atual", "Current password")}<input name="current_password" type="password" autoComplete="current-password" required /></label>
              <label>{t("Nova senha", "New password")}<input name="new_password" type="password" autoComplete="new-password" minLength={12} required /></label>
              <button disabled={busy}>{t("Alterar senha", "Change password")}</button>
            </form>
            <form className="grid content-start gap-3" onSubmit={(event) => save(event, "recovery")}>
              <label>{t("Senha atual", "Current password")}<input name="current_password" type="password" autoComplete="current-password" /></label>
              <label>{t("Ou código de recuperação", "Or recovery code")}<input name="recovery_code" autoComplete="one-time-code" /></label>
              <button disabled={busy}>{t("Gerar novos códigos", "Generate new codes")}</button>
            </form>
          </div>
          {codes.length > 0 && <RecoveryCodes codes={codes} />}
        </details>
      </>}
    </>}
  </div>;
}
