import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

const nav = [
  { to: "/", label: "A · ERP Grid" },
  { to: "/wave", label: "B · Wave Terminal" },
  { to: "/scoreboard", label: "E · Scoreboard" },
] as const;

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="relative z-10 min-h-screen">
      <header className="sticky top-0 z-20 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center gap-8 px-6 py-3">
          <Link to="/" className="flex items-center gap-3">
            <span className="grid h-7 w-7 place-items-center bg-primary num text-xs font-bold text-primary-foreground">H</span>
            <span className="font-semibold tracking-tight">Hollerau Agentic Command</span>
          </Link>
          <nav className="flex gap-1">
            {nav.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                activeOptions={{ exact: true }}
                className="px-3 py-1.5 num text-xs text-muted-foreground hover:text-foreground"
                activeProps={{ className: "px-3 py-1.5 num text-xs text-primary border-b-2 border-primary" }}
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 num text-xs text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-success" /> LIVE SYNC
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1500px] px-6 py-8">{children}</main>
    </div>
  );
}

export function MindsetBadge({ m }: { m?: string | null | undefined }) {
  if (!m) return <span className="label-caps">—</span>;
  const cls =
    m === "Stalled"
      ? "border-warning text-warning"
      : m === "Critical_Breakoff"
        ? "border-destructive text-destructive"
        : "border-success text-success";
  return <span className={`border px-1.5 py-0.5 num text-[10px] uppercase tracking-wider ${cls}`}>{m.replace("_", " ")}</span>;
}

export function StatusDot({ s }: { s: string }) {
  const c =
    s === "active"
      ? "bg-primary"
      : s === "deal"
        ? "bg-success"
        : s === "walked_away" || s === "error"
          ? "bg-destructive"
          : "bg-muted-foreground";
  return (
    <span className="inline-flex items-center gap-1.5 num text-xs">
      <span className={`h-1.5 w-1.5 rounded-full ${c}`} />
      {s.replace("_", " ")}
    </span>
  );
}
