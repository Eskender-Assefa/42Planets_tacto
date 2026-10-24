import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, MindsetBadge, StatusDot } from "@/components/Shell";
import { useCaseOverview, useSuppliers, supplierNames, eur, scoreLabel } from "@/lib/command";
import type { Environment } from "@/integrations/hollerau/types";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "ERP Master Grid · Hollerau Agentic Command" },
      { name: "description", content: "All autonomous procurement negotiations with live cost, floor and score." },
      { property: "og:title", content: "ERP Master Grid · Hollerau Agentic Command" },
      { property: "og:description", content: "All autonomous procurement negotiations with live cost, floor and score." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Grid,
});

const ENVIRONMENTS: Environment[] = ["sim", "practice", "final"];

function Grid() {
  const [env, setEnv] = useState<Environment | null>(null);
  const [wave, setWave] = useState<number | null>(null);
  const { query, latestEnvironment } = useCaseOverview(env, wave);
  const suppliers = useSuppliers();
  const data = query.data ?? [];
  const activeEnv = env ?? latestEnvironment;
  const waves = [...new Set(data.map((c) => c.wave).filter((w): w is number => w != null))].sort((a, b) => a - b);
  const active = data.filter((c) => c.status === "active").length;
  const deals = data.filter((c) => c.status === "deal").length;

  return (
    <Shell>
      <div className="mb-6 flex flex-wrap items-center gap-2">
        {ENVIRONMENTS.map((e) => (
          <button
            key={e}
            onClick={() => setEnv(e)}
            className={`border px-3 py-1.5 num text-xs uppercase tracking-wider ${activeEnv === e ? "border-primary text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
          >
            {e}
          </button>
        ))}
        <span className="mx-2 h-4 w-px bg-border" />
        <button
          onClick={() => setWave(null)}
          className={`border px-3 py-1.5 num text-xs uppercase tracking-wider ${wave == null ? "border-primary text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
        >
          All waves
        </button>
        {waves.map((w) => (
          <button
            key={w}
            onClick={() => setWave(w)}
            className={`border px-3 py-1.5 num text-xs uppercase tracking-wider ${wave === w ? "border-primary text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
          >
            Wave {w}
          </button>
        ))}
      </div>

      <div className="mb-8 grid grid-cols-3 gap-px border border-border bg-border">
        {[
          ["Cases", String(data.length)],
          ["Active", String(active)],
          ["Deals", String(deals)],
        ].map(([k, v]) => (
          <div key={k} className="bg-card p-5">
            <div className="label-caps">{k}</div>
            <div className="mt-2 num text-3xl font-semibold">{v}</div>
          </div>
        ))}
      </div>

      <div className="panel overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              {["Session", "Case", "Suppliers", "Category goal", "Wave", "Turn", "C open", "Last offer", "C best", "Score", "Mindset", "Status", ""].map((h) => (
                <th key={h} className="px-4 py-3 label-caps font-normal">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {query.isLoading && (
              <tr><td colSpan={13} className="px-4 py-8 text-center text-muted-foreground">Loading…</td></tr>
            )}
            {!query.isLoading && data.length === 0 && (
              <tr><td colSpan={13} className="px-4 py-8 text-center text-muted-foreground">No cases yet — start the runner.</td></tr>
            )}
            {data.map((c) => (
              <tr key={c.session_id} className="border-b border-border/60 hover:bg-accent/40">
                <td className="px-4 py-3 num text-xs text-muted-foreground">{c.session_id}</td>
                <td className="px-4 py-3 font-medium">{c.title ?? c.case_id}</td>
                <td className="px-4 py-3">{supplierNames(c, suppliers.data)}</td>
                <td className="px-4 py-3 text-muted-foreground">{c.category_goal ?? "—"}</td>
                <td className="px-4 py-3 num">{c.wave ?? "—"}</td>
                <td className="px-4 py-3 num">{c.last_turn ?? "—"}</td>
                <td className="px-4 py-3 num">{eur(c.c_open)}</td>
                <td className="px-4 py-3 num text-primary">{eur(c.last_c_supplier_offer)}</td>
                <td className="px-4 py-3 num">{eur(c.c_best)}</td>
                <td className="px-4 py-3 num">{scoreLabel(c.score)}</td>
                <td className="px-4 py-3"><MindsetBadge m={c.last_mindset} /></td>
                <td className="px-4 py-3"><StatusDot s={c.status} /></td>
                <td className="px-4 py-3">
                  <Link to="/audit/$sessionId" params={{ sessionId: c.session_id }} className="num text-xs text-primary hover:underline">
                    Audit →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
