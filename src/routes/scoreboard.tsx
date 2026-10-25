import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, XAxis, YAxis } from "recharts";
import { Shell } from "@/components/Shell";
import { useWaveScores, useCaseOverview, scoreLabel } from "@/lib/command";
import { bestCaseScores, percentScore } from "@/lib/telemetry";
import { Button } from "@/components/ui/button";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import type { Environment } from "@/integrations/hollerau/types";

export const Route = createFileRoute("/scoreboard")({
  head: () => ({
    meta: [
      { title: "Scoreboard · Hollerau Agentic Command" },
      { name: "description", content: "Cases played, deals and scores per environment and wave." },
      { property: "og:title", content: "Scoreboard · Hollerau Agentic Command" },
      { property: "og:description", content: "Cases played, deals and scores per environment and wave." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Scoreboard,
});

function Scoreboard() {
  const { data = [], isLoading } = useWaveScores();
  const [environment, setEnvironment] = useState<Environment | null>(null);
  const { query, latestEnvironment } = useCaseOverview(environment, null);
  const navigate = useNavigate();
  const scores = bestCaseScores(query.data ?? []);
  const plotted = scores.filter((c): c is typeof c & { score: number } => c.score != null).map((c) => ({ ...c, label: `${c.caseId} · ${c.caseType}`, percent: c.score * 100 }));
  const types = [...new Set((query.data ?? []).map((c) => c.case_type ?? "-"))].sort();
  const colors = ["var(--chart-1)", "var(--chart-2)", "var(--info)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--chart-6)", "var(--chart-7)"];
  const categories = ["bundling", "capacity", "price_increase", "quality", "raw_material", "renewal", "rfq"];
  const colorFor = (type: string) => colors[categories.includes(type) ? categories.indexOf(type) : 7];
  const mean = plotted.length ? plotted.reduce((sum, c) => sum + c.percent, 0) / plotted.length : null;

  return (
    <Shell>
      <div className="mb-6">
        <div className="label-caps">E · Results</div>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">Scoreboard</h1>
      </div>
      <div className="mb-5 flex gap-2">{(["sim", "practice", "final"] as Environment[]).map((e) => <Button key={e} variant={(environment ?? latestEnvironment) === e ? "secondary" : "outline"} size="sm" onClick={() => setEnvironment(e)} className="num uppercase">{e}</Button>)}</div>
      <section className="mb-8 border-y border-border py-5">
        <h2 className="mb-4 text-xl font-semibold">Score by case</h2>
        {query.isLoading ? <p className="py-8 text-muted-foreground">Loading…</p> : !plotted.length ? <p className="py-8 text-muted-foreground">-</p> : <>
          <ChartContainer config={{ percent: { label: "Score", color: "var(--primary)" } }} className="w-full aspect-auto" style={{ height: Math.max(260, plotted.length * 48 + 60) }}>
            <BarChart accessibilityLayer data={plotted} layout="vertical" margin={{ top: 15, right: 40, left: 0, bottom: 10 }}>
              <CartesianGrid horizontal={false} stroke="var(--border)" />
              <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="label" width={155} tickLine={false} axisLine={false} />
              <ChartTooltip content={<ChartTooltipContent labelFormatter={(_, p) => p[0]?.payload.label ?? "-"} formatter={(value) => <span className="num">{Number(value).toFixed(1)} %</span>} />} />
              {mean != null && <ReferenceLine x={mean} stroke="var(--foreground)" strokeDasharray="4 4" label={{ value: `Mean ${mean.toFixed(1)}%`, position: "top", fill: "var(--muted-foreground)", fontSize: 10 }} />}
              <Bar dataKey="percent" maxBarSize={28} isAnimationActive={false} cursor="pointer" onClick={(_, index) => { const row = plotted[index]; if (row) void navigate({ to: "/audit/$sessionId", params: { sessionId: row.sessionId } }); }}>
                {plotted.map((c) => <Cell key={c.caseId} fill={colorFor(c.caseType)} />)}
              </Bar>
            </BarChart>
          </ChartContainer>
          <div className="mt-4 flex flex-wrap gap-4 text-xs">{types.map((type) => <span key={type} className="flex items-center gap-2"><svg width="10" height="10" aria-hidden="true"><rect width="10" height="10" fill={colorFor(type)} /></svg>{type}</span>)}</div>
        </>}
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs">{scores.map((c) => <Link key={c.caseId} to="/audit/$sessionId" params={{ sessionId: c.sessionId }} className="num text-muted-foreground hover:text-primary">{c.caseId} · {percentScore(c.score)} →</Link>)}</div>
      </section>
      <div className="panel overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              {["Environment", "Wave", "Cases played", "Deals", "Avg score", "Total score"].map((h) => (
                <th key={h} className="px-4 py-3 label-caps font-normal">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">Loading…</td></tr>
            )}
            {!isLoading && data.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No cases yet — start the runner.</td></tr>
            )}
            {data.filter((w) => w.environment === (environment ?? latestEnvironment)).map((w) => (
              <tr key={`${w.environment}-${w.wave ?? "all"}`} className="border-b border-border/60">
                <td className="px-4 py-3 num text-xs uppercase tracking-wider">{w.environment}</td>
                <td className="px-4 py-3 num">{w.wave ?? "-"}</td>
                <td className="px-4 py-3 num">{w.cases_played}</td>
                <td className="px-4 py-3 num text-primary">{w.deals}</td>
                <td className="px-4 py-3 num">{scoreLabel(w.avg_score)}</td>
                <td className="px-4 py-3 num">{w.total_score.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
