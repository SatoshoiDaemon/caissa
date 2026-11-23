"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { api, errorMessage, type User } from "../../client/api";
import { RecoveryCodes } from "../../components/recovery-codes";
import { Feedback, useApp } from "../../components/shell";

type Mode = "login" | "register" | "recovery";

export default function Login() {
  const { t, setUser } = useApp();
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [codes, setCodes] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [recovered, setRecovered] = useState(false);
  const [busy, setBusy] = useState(false);
  const labels = { login: t("Entrar", "Sign in"), register: t("Criar conta", "Create account"),
    recovery: t("Recuperar acesso", "Recover account") };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result = await api<{ user: User; recovery_codes?: string[] }>("/auth/" + mode, {
        method: "POST", body: Object.fromEntries(new FormData(event.currentTarget)),
      });
      if (mode === "recovery") {
        setUser(null);
        setRecovered(true);
        setMode("login");
      } else {
        setUser(result.user);
        if (result.recovery_codes?.length) setCodes(result.recovery_codes);
        else router.push("/lobby");
      }
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }

  return <section className="panel mx-auto grid max-w-xl gap-5">
    <h1>{codes.length ? t("Códigos de recuperação", "Recovery codes") : labels[mode]}</h1>
    {codes.length ? <>
      <RecoveryCodes codes={codes} />
      <Link href="/lobby">{t("Ir para o lobby", "Go to lobby")}</Link>
    </> : <>
      <Feedback error={error} />
      {recovered && <p role="status">{t("Senha redefinida. Entre com a nova senha.", "Password reset. Sign in with the new password.")}</p>}
      <form key={mode} onSubmit={submit} className="grid gap-3">
        <label>{t("Usuário", "Username")}<input name="username" autoComplete="username" required maxLength={24} /></label>
        {mode === "recovery" && <label>{t("Código de recuperação", "Recovery code")}<input name="recovery_code" autoComplete="one-time-code" required /></label>}
        <label>{mode === "recovery" ? t("Nova senha", "New password") : t("Senha", "Password")}
          <input name={mode === "recovery" ? "new_password" : "password"} type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={mode === "login" ? undefined : 12} required />
        </label>
        <button disabled={busy} className="primary">{labels[mode]}</button>
      </form>
      <div className="flex flex-wrap gap-2">{(Object.keys(labels) as Mode[]).filter((key) => key !== mode).map((key) =>
        <button key={key} disabled={busy} onClick={() => { setError(""); setRecovered(false); setMode(key); }}>{labels[key]}</button>
      )}</div>
    </>}
  </section>;
}
