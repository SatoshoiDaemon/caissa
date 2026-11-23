"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, errorMessage, type Color, type Game, type Move, type Piece, type Promotion } from "../client/api";
import { Board, glyph } from "./board";
import { Feedback, useApp } from "./shell";

export function resultLabel(status: string, t: (pt: string, en: string) => string) {
  const labels: Record<string, string> = {
    active: t("Em jogo", "In progress"), checkmate: t("Xeque-mate", "Checkmate"),
    stalemate: t("Afogamento", "Stalemate"), draw: t("Empate", "Draw"),
    resignation: t("Desistência", "Resignation"), timeout: t("Tempo esgotado", "Time expired"),
    abandonment: t("Abandono", "Abandonment"), imported: t("Importada", "Imported"),
  };
  return labels[status] ?? status;
}

export function Moves({ moves, step, onStep }: { moves: Move[]; step?: number; onStep?: (step: number) => void }) {
  const { t } = useApp();
  return <section className="panel grid gap-3">
    <h2>{t("Lances", "Moves")}</h2>
    {moves.length === 0 ? <p className="muted">{t("Nenhum lance feito.", "No moves yet.")}</p>
      : <ol className="code grid grid-cols-2 gap-2 max-h-64 overflow-auto" aria-label={t("Histórico de lances", "Move history")}>
        {moves.map((move, index) => <li key={index}>
          {onStep ? <button aria-current={index + 1 === step ? "step" : undefined} onClick={() => onStep(index + 1)}>
            {index + 1}. {move.san || move.from + "–" + move.to}
          </button> : <span>{index + 1}. {move.san || move.from + "–" + move.to}</span>}
        </li>)}
      </ol>}
  </section>;
}

function Clock({ value }: { value: number | null }) {
  if (value === null) return <span className="code">—</span>;
  const seconds = Math.ceil(value / 1000);
  return <span className="code text-xl font-bold">{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}</span>;
}

export function Arena({ game, color = "white", local = false, playable, send }: {
  game: Game; color?: Color; local?: boolean; playable: boolean;
  send: (event: string, move?: Move, actor?: Color) => Promise<void>;
}) {
  const { t } = useApp();
  const [selection, setSelection] = useState<{square: string; version: number; targets: string[]}>();
  const [promotion, setPromotion] = useState<(Move & {version: number})>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  const active = game.status === "active";
  const actor = local ? game.current_player : color;
  const selected = selection?.version === game.version ? selection : undefined;
  const canMove = playable && active && (local || !!game.black_player) && actor === game.current_player && !busy;
  const colorLabel = (side: Color) => side === "white" ? t("Brancas", "White") : t("Pretas", "Black");

  async function command(event: string, move?: Move) {
    setBusy(true);
    setError("");
    try { await send(event, move, actor); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }

  async function squareClick(square: string, piece: Piece | null) {
    if (!canMove) return;
    pending.current?.abort();
    setError("");
    if (selected?.targets.includes(square)) {
      const [file, rank] = selected.square;
      const moving = game.board[8 - Number(rank)]["abcdefgh".indexOf(file)];
      const move = { from: selected.square, to: square };
      setSelection(undefined);
      if (moving?.type === "p" && /[18]$/.test(square)) setPromotion({ ...move, version: game.version });
      else await command("make_move", move);
    } else if (piece?.color === actor && selected?.square !== square) {
      const controller = new AbortController();
      pending.current = controller;
      setSelection({ square, version: game.version, targets: [] });
      try {
        const { possible_moves } = await api<{possible_moves: string[]}>(
          "/games/" + game.game_id + "/moves/" + square, { signal: controller.signal },
        );
        if (!controller.signal.aborted) setSelection({ square, version: game.version, targets: possible_moves });
      } catch (err) { if (!controller.signal.aborted) setError(errorMessage(err)); }
    } else setSelection(undefined);
  }

  const offering = game.draw_offer.offered_by;
  const waiting = !local && !game.black_player;
  const top = color === "white" ? "black" : "white";
  function playerBar(side: Color) {
    return <div className="panel flex flex-wrap items-center justify-between gap-3">
      <div>
        <strong>{game[side + "_player" as "white_player" | "black_player"] ?? colorLabel(side)}</strong>
        {!local && <span className="muted ml-2 text-sm">{game[side + "_connected" as "white_connected" | "black_connected"]
          ? t("Online", "Online") : t("Desconectado", "Disconnected")}</span>}
      </div>
      {!local && <div className={game.active_clock_color === side ? "clock-active" : ""}>
        <Clock value={game[side + "_time_remaining_ms" as "white_time_remaining_ms" | "black_time_remaining_ms"]} />
      </div>}
    </div>;
  }

  return <div className="arena">
    <div className="grid gap-2">
      {playerBar(top)}
      <Board position={game.board} orientation={color} selected={selected?.square} targets={selected?.targets}
        onSquare={playable && active ? squareClick : undefined} />
      {playerBar(color)}
    </div>
    <aside className="grid gap-3">
      <section className="panel grid gap-3">
        <h2 aria-live="polite">{waiting && active ? t("Aguardando oponente", "Waiting for opponent")
          : active ? colorLabel(game.current_player) + (game.in_check ? t(" em xeque", " in check") : t(" jogam", " to move"))
          : resultLabel(game.status, t)}</h2>
        {game.winner && <p>{colorLabel(game.winner)} {t("venceram", "won")}</p>}
        {!active && <Link href={"/games/" + game.game_id}>{t("Rever partida", "Review game")}</Link>}
        {active && !waiting && playable && <div className="flex flex-wrap gap-2">
          {offering && offering !== actor && !local ? <>
            <button disabled={busy} onClick={() => command("accept_draw")}>{t("Aceitar empate", "Accept draw")}</button>
            <button disabled={busy} onClick={() => command("decline_draw")}>{t("Recusar empate", "Decline draw")}</button>
          </> : !local && <button disabled={busy || !!offering} onClick={() => command("offer_draw")}>
            {offering ? t("Empate oferecido", "Draw offered") : t("Oferecer empate", "Offer draw")}
          </button>}
          <button disabled={busy} onClick={() => {
            if (window.confirm(t("Desistir da partida?", "Resign this game?"))) void command("resign_game");
          }}>{t("Desistir", "Resign")}</button>
        </div>}
        {promotion?.version === game.version && canMove && <div className="grid gap-2" role="group" aria-label={t("Promoção", "Promotion")}>
          <p>{t("Escolha a peça para promoção", "Choose a promotion piece")}</p>
          <div className="flex flex-wrap gap-2">
            {(["q", "r", "b", "n"] as Promotion[]).map((type, index) => <button key={type}
              aria-label={[t("Dama", "Queen"), t("Torre", "Rook"), t("Bispo", "Bishop"), t("Cavalo", "Knight")][index]}
              onClick={() => {
                setPromotion(undefined);
                void command("make_move", { from: promotion.from, to: promotion.to, promotion: type });
              }}>{glyph[type]}</button>)}
            <button onClick={() => setPromotion(undefined)}>{t("Cancelar", "Cancel")}</button>
          </div>
        </div>}
        <Feedback error={error} />
      </section>
      <Moves moves={game.move_history} />
    </aside>
  </div>;
}
