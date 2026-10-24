import { createFileRoute, Link } from "@tanstack/react-router";
import { Shell, MindsetBadge, StatusDot } from "@/components/Shell";
import { useCases, eur } from "@/lib/command";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "ERP Master Grid · Hollerau Agentic Command" },
      { name: "description", content: "All autonomous procurement negotiations with live cost, floor and score." },
      { property: "og:title", content: "ERP Master Grid · Hollerau Agentic Command" },
      { property: "og:description", content: "All autonomous procurement negotiations with live cost, floor and score." },
    ],
  }),
  component: Grid,
});

function Grid() {
  const { data = [], isLoading } = useCases();
  const active = data.filter((c) => c.status === "Active").length;
  const saved = data.reduce((s, c) => s + (Number(c.c_open) - Number(c.c_current_offer)), 0);
  const avg = data.length ? data.reduce((s, c) => s + Number(c.current_score), 0) / data.length : 0;

  return (
    <Shell>
      <div className="mb-8 grid grid-cols-2 gap-px border border-border bg-border md:grid-cols-4">
        {[
          ["Cases", String(data.length)],
          ["Active", String(active)],
          ["Yield secured", eur(saved)],
          ["Avg score", avg.toFixed(3)],
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
              {["Session", "Supplier", "Segment", "Country", "Wave", "Turn", "C open", "Offer", "Floor", "Score", "Mindset", "Status", ""].map((h) => (
                <th key={h} className="px-4 py-3 label-caps font-normal">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={13} className="px-4 py-8 text-center text-muted-foreground">Loading…</td></tr>
            )}
            {data.map((c) => (
              <tr key={c.session_id} className="border-b border-border/60 hover:bg-accent/40">
                <td className="px-4 py-3 num text-xs text-muted-foreground">{c.session_id}</td>
                <td className="px-4 py-3 font-medium">{c.supplier?.name}</td>
                <td className="px-4 py-3 text-muted-foreground">{c.supplier?.segment}</td>
                <td className="px-4 py-3 text-muted-foreground">{c.supplier?.country}</td>
                <td className="px-4 py-3 num">{c.wave_number}</td>
                <td className="px-4 py-3 num">{c.turn_number}</td>
                <td className="px-4 py-3 num">{eur(c.c_open)}</td>
                <td className="px-4 py-3 num text-primary">{eur(c.c_current_offer)}</td>
                <td className="px-4 py-3 num">{eur(c.c_best_floor)}</td>
                <td className="px-4 py-3 num">{Number(c.current_score).toFixed(3)}</td>
                <td className="px-4 py-3"><MindsetBadge m={c.mindset} /></td>
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
