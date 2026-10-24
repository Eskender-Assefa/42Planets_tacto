import { createFileRoute } from "@tanstack/react-router";
import { Shell } from "@/components/Shell";
import { useWaveScores, scoreLabel } from "@/lib/command";

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

  return (
    <Shell>
      <div className="mb-6">
        <div className="label-caps">E · Results</div>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">Scoreboard</h1>
      </div>
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
            {data.map((w) => (
              <tr key={`${w.environment}-${w.wave ?? "all"}`} className="border-b border-border/60">
                <td className="px-4 py-3 num text-xs uppercase tracking-wider">{w.environment}</td>
                <td className="px-4 py-3 num">{w.wave ?? "—"}</td>
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
