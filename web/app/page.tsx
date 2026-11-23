"use client";

import Link from "next/link";
import { useApp } from "../components/shell";

export default function Home() {
  const { t } = useApp();
  return <section className="panel grid items-center gap-8 md:grid-cols-2">
    <div className="grid justify-items-start gap-5 py-8">
      <h1>{t("O próximo lance é seu.", "Your move.")}</h1>
      <p className="muted text-lg">{t("Jogue xadrez em tempo real com amigos ou divida o tabuleiro no mesmo dispositivo.", "Play chess with friends in real time or share the board on one device.")}</p>
      <Link className="action primary" href="/lobby">{t("Abrir lobby", "Open lobby")}</Link>
    </div>
    <img className="mx-auto w-48 md:w-64" src="/caissa-logo.png" alt="" />
  </section>;
}
