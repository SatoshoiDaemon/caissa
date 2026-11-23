"use client";

import Link from "next/link";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { ApiError, api, type User } from "../client/api";

type Language = "pt-BR" | "en-US";
type Context = {
  lang: Language; t: (pt: string, en: string) => string;
  user: User | null; setUser: (user: User | null) => void; loading: boolean;
};
const Session = createContext<Context>({
  lang: "pt-BR", t: (pt) => pt, user: null, setUser: () => {}, loading: true,
});

export const useApp = () => useContext(Session);

export function Shell({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Language>("pt-BR");
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (localStorage.getItem("caissa:language") === "en-US") setLang("en-US");
    const controller = new AbortController();
    api<{user: User}>("/auth/me", { signal: controller.signal })
      .then(({ user }) => setUser(user))
      .catch((err) => {
        if (!controller.signal.aborted && !(err instanceof ApiError && err.status === 401)) {
          setError(true);
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const t = (pt: string, en: string) => lang === "pt-BR" ? pt : en;

  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      setUser(null);
      setError(false);
    } catch { setError(true); }
  }

  return <Session.Provider value={{ lang, t, user, setUser, loading }}>
    <header className="site-header">
      <Link href="/" className="brand"><img src="/caissa-logo.png" alt="" width="40" height="40" />Caissa</Link>
      <nav aria-label={t("Navegação principal", "Main navigation")} className="flex flex-wrap items-center gap-4">
        <Link href="/lobby">Lobby</Link>
        {user ? <>
          <Link href={"/u/" + encodeURIComponent(user.username)}>{user.username}</Link>
          <button onClick={logout}>{t("Sair", "Sign out")}</button>
        </> : !loading && <Link href="/login">{t("Entrar", "Sign in")}</Link>}
        <select aria-label={t("Idioma", "Language")} value={lang} onChange={(event) => {
          const next = event.target.value as Language;
          localStorage.setItem("caissa:language", next);
          setLang(next);
        }}>
          <option value="pt-BR">PT</option><option value="en-US">EN</option>
        </select>
      </nav>
    </header>
    <main className="container">
      {error && <p role="alert">{t("Não foi possível atualizar a sessão.", "Could not update your session.")}</p>}
      {children}
    </main>
  </Session.Provider>;
}

const errors: Record<string, [string, string]> = {
  request_failed: ["Não foi possível acessar o servidor.", "Could not reach the server."],
  "Failed to fetch": ["A conexão com o servidor falhou.", "Connection to the server failed."],
  "room is full": ["A sala está cheia.", "The room is full."],
  "room not found": ["Sala não encontrada.", "Room not found."],
  "room is not public": ["A sala é privada.", "The room is private."],
  "authentication required": ["Entre na sua conta para continuar.", "Sign in to continue."],
  "invalid move": ["Lance inválido.", "Invalid move."],
  "invalid player token": ["Sua vaga nesta partida não está disponível.", "Your seat in this game is unavailable."],
  "game is still in progress": ["A partida ainda está em andamento.", "The game is still in progress."],
  "invalid username or password": ["Nome de usuário ou senha inválidos.", "Invalid username or password."],
  "rate limit exceeded": ["Muitas tentativas. Aguarde um momento.", "Too many attempts. Try again shortly."],
};

export function Feedback({ error }: { error: string }) {
  const { lang, t } = useApp();
  if (!error) return null;
  const translated = errors[error];
  return <p role="alert" className="error">{translated
    ? t(...translated)
    : lang === "en-US" ? error : t("O servidor recusou a solicitação.", "The server rejected the request.")}</p>;
}
