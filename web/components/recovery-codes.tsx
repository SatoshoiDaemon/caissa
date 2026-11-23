"use client";

import { useApp } from "./shell";

export function RecoveryCodes({ codes }: { codes: string[] }) {
  const { t } = useApp();
  return <div className="grid gap-3">
    <p>{t("Guarde estes códigos agora. Eles aparecem uma única vez.", "Save these codes now. They are shown only once.")}</p>
    <pre className="code select-all">{codes.join("\n")}</pre>
    <a download="caissa-recovery.txt" href={"data:text/plain;charset=utf-8," + encodeURIComponent(codes.join("\n"))}>
      {t("Baixar códigos", "Download codes")}
    </a>
  </div>;
}
