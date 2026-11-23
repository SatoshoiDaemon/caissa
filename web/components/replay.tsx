"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, errorMessage, type BoardState, type Game } from "../client/api";
import { Moves, resultLabel } from "./arena";
import { Board } from "./board";
import { Feedback, useApp } from "./shell";

export function Replay({ id }: { id: string }) {
  const { t } = useApp();
  const [game, setGame] = useState<Game & {positions: BoardState[]}>();
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    api<Game & {positions: BoardState[]}>("/games/" + encodeURIComponent(id) + "/replay", { signal: controller.signal })
      .then(setGame).catch((err) => { if (!controller.signal.aborted) setError(errorMessage(err)); });
    return () => controller.abort();
  }, [id]);

  return <div className="grid gap-4">
    <h1>{t("Rever partida", "Review game")}</h1>
    <Feedback error={error} />
    {game ? <>
      <p>{game.white_player} × {game.black_player} · {resultLabel(game.status, t)}</p>
      <div className="arena">
        <div className="grid gap-3">
          <Board position={game.positions[step]} />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <button disabled={step === 0} onClick={() => setStep(step - 1)}>{t("Anterior", "Previous")}</button>
            <span className="code" aria-live="polite">{step} / {game.move_history.length}</span>
            <button disabled={step === game.move_history.length} onClick={() => setStep(step + 1)}>{t("Próximo", "Next")}</button>
          </div>
        </div>
        <div className="grid content-start gap-3">
          <Moves moves={game.move_history} step={step} onStep={setStep} />
          <a download={id + ".pgn"} href={"/api/v1/games/" + encodeURIComponent(id) + "/pgn"}>{t("Baixar PGN", "Download PGN")}</a>
        </div>
      </div>
    </> : !error && <p role="status">{t("Carregando partida…", "Loading game…")}</p>}
  </div>;
}

export function ImportPgn() {
  const { t } = useApp();
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const game = await api<Game>("/games/import", { method: "POST", body: Object.fromEntries(new FormData(event.currentTarget)) });
      router.push("/games/" + game.game_id);
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  return <details className="panel">
    <summary className="cursor-pointer">{t("Importar PGN", "Import PGN")}</summary>
    <form className="mt-4 grid gap-3" onSubmit={submit}>
      <label>PGN<textarea name="pgn" rows={5} maxLength={15000} required /></label>
      <Feedback error={error} />
      <button disabled={busy}>{t("Importar", "Import")}</button>
    </form>
  </details>;
}
