import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Shell } from "../components/shell";
import "./styles.css";

export const metadata: Metadata = { title: "Caissa", description: "Xadrez casual em tempo real" };

export default function Layout({ children }: { children: ReactNode }) {
  return <html lang="pt-BR"><body><Shell>{children}</Shell></body></html>;
}
