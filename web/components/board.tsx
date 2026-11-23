"use client";

import type { BoardState, Color, Piece } from "../client/api";
import { useApp } from "./shell";

export const glyph: Record<Piece["type"], string> = { k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟" };

export function Board({ position, orientation = "white", selected, targets, onSquare }: {
  position: BoardState; orientation?: Color; selected?: string;
  targets?: string[]; onSquare?: (square: string, piece: Piece | null) => void;
}) {
  const { t } = useApp();
  const names = { k: t("rei", "king"), q: t("dama", "queen"), r: t("torre", "rook"),
    b: t("bispo", "bishop"), n: t("cavalo", "knight"), p: t("peão", "pawn") };

  return <div className="board" role="group" aria-label={t("Tabuleiro", "Chessboard")}>
    {Array.from({ length: 64 }, (_, index) => {
      const actual = orientation === "white" ? index : 63 - index;
      const row = Math.floor(actual / 8);
      const column = actual % 8;
      const square = "abcdefgh"[column] + (8 - row);
      const piece = position[row][column];
      const label = piece ? square + " " + names[piece.type] + " · " +
        (piece.color === "white" ? t("brancas", "white") : t("pretas", "black")) : square;
      const className = ["square", (row + column) % 2 === 0 ? "light" : "dark",
        selected === square ? "selected" : "", targets?.includes(square) ? "target" : ""].join(" ");
      const content = <>
        {piece && <span className={"piece-" + piece.color} aria-hidden="true">{glyph[piece.type]}</span>}
        {(index >= 56 || index % 8 === 0) && <small className="coordinate" aria-hidden="true">{square}</small>}
      </>;
      return onSquare ? <button type="button" key={square} className={className} aria-label={label}
        aria-pressed={selected === square} data-square={square} onClick={() => onSquare(square, piece)}>{content}</button>
        : <div key={square} className={className} aria-label={label}>{content}</div>;
    })}
  </div>;
}
