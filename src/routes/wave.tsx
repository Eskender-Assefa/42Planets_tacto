import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Shell, MindsetBadge, StatusDot } from "@/components/Shell";
import { useCaseOverview, useSuppliers, supplierNames, eur, clock, scoreLabel, secondsRemaining } from "@/lib/command";
import type { CaseOverview, Environment } from "@/integrations/hollerau/types";
import { CostBar, ProtocolProfile } from "@/components/Telemetry";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/wave")({
  head: () => ({
    meta: [
      { title: "Live Wave Terminal · Hollerau Agentic Command" },
      { name: "description", content: "Parallel negotiation cards with countdowns, live offers and supplier mindset." },
      { property: "og:title", content: "Live Wave Terminal · Hollerau Agentic Command" },
      { property: "og:description", content: "Parallel negotiation cards with countdowns, live offers and supplier mindset." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Wave,
});

const ENVIRONMENTS: Environment[] = ["sim", "practice", "final"];
const MAX_SECONDS = 600;

function Wave() {
  const [env, setEnv] = useState<Environment | null>(null);
  const [wave, setWave] = useState<number | null>(null);
  const { query, latestEnvironment } = useCaseOverview(env, wave);
  const suppliers = useSuppliers();
  const data = query.data ?? [];
  const activeEnv = env ?? latestEnvironment;
  const waves = [...new Set(data.map((c) => c.wave).filter((w): w is number => w != null))].sort((a, b) => a - b);

  return (
    <Shell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="label-caps">Wave terminal · {activeEnv ?? "…"}</div>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Live Wave Terminal</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {ENVIRONMENTS.map((e) => (
            <Button variant="outline" size="sm"
              key={e}
              onClick={() => setEnv(e)}
              className={`border px-3 py-1.5 num text-xs uppercase tracking-wider ${activeEnv === e ? "border-primary text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
            >
              {e}
            </Button>
          ))}
          <span className="mx-1 h-4 w-px bg-border" />
          <Button variant="outline" size="sm"
            onClick={() => setWave(null)}
            className={`border px-3 py-1.5 num text-xs uppercase tracking-wider ${wave == null ? "border-primary text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
          >
            All
          </Button>
          {waves.map((w) => (
            <Button variant="outline" size="sm"
              key={w}
              onClick={() => setWave(w)}
              className={`border px-3 py-1.5 num text-xs uppercase tracking-wider ${wave === w ? "border-primary text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
            >
              W{w}
            </Button>
          ))}
        </div>
      </div>

      {!query.isLoading && data.length === 0 && (
        <div className="panel p-10 text-center text-muted-foreground">No cases yet — start the runner.</div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
        {data.map((c) => <WaveCard key={c.session_id} c={c} suppliers={suppliers.data} />)}
      </div>
    </Shell>
  );
}

function WaveCard({ c, suppliers }: { c: CaseOverview; suppliers: ReturnType<typeof useSuppliers>["data"] }) {
  const active = c.status === "active";
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [active]);

  const secs = secondsRemaining(c, now);
  const critical = active && secs != null && secs < 60;
  const stalled = c.last_mindset === "Stalled";

  return (
    <Link
      to="/audit/$sessionId"
      params={{ sessionId: c.session_id }}
      className={`panel flex flex-col gap-4 p-4 transition hover:-translate-y-0.5 ${active ? "live" : "opacity-55"} ${stalled && active ? "border-warning" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-semibold leading-tight">{c.title ?? c.case_id}</div>
          <div className="mt-0.5 text-xs text-muted-foreground">{supplierNames(c, suppliers)}</div>
        </div>
        <StatusDot s={c.status} />
      </div>

      <ProtocolProfile c={c} suppliers={suppliers} />

      <div>
        <div className="flex justify-between">
          <span className="label-caps">Turn {c.last_turn ?? "-"}</span>
          <span className={`num text-sm ${critical ? "text-destructive" : ""}`}>{secs == null ? "-" : clock(secs)}</span>
        </div>
        <div className="mt-1 h-1 bg-muted">
          <div
            className={`h-full ${critical ? "bg-destructive" : "bg-primary"}`}
            style={{ width: `${secs == null ? 0 : Math.min(100, (secs / MAX_SECONDS) * 100)}%` }}
          />
        </div>
      </div>

      <CostBar c={c} />

      <div className="mt-auto flex items-center justify-between border-t border-border pt-3">
        <MindsetBadge m={c.last_mindset} />
        <span className="num text-2xl font-semibold">{scoreLabel(c.score)}</span>
      </div>
    </Link>
  );
}
