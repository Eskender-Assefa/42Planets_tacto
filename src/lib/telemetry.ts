import type { DecisionSource } from "@/integrations/hollerau/types";

export const decisionLabels: Record<DecisionSource, string> = {
  claude: "Claude", fallback: "Fallback", rule: "Rule", closing: "Time-cap close", naive: "Naive",
};

export const displayText = (value: string | null | undefined) => value?.trim() ? value : "-";
export const decisionLabel = (source: DecisionSource | null | undefined) => source ? decisionLabels[source] ?? "-" : "-";
export const latencyLabel = (ms: number | null | undefined) => ms == null ? "-" : `${(ms / 1000).toFixed(1)} s`;
export const velocityLabel = (velocity: number | null | undefined) => velocity == null ? "-" : `${(velocity * 100).toFixed(2)}% of C_open / round`;

export function protocolTone(protocol: string | null | undefined) {
  if (protocol?.startsWith("Leverage")) return "success";
  if (protocol?.startsWith("Strategic") || protocol?.startsWith("Bottleneck")) return "warning";
  if (protocol?.startsWith("Quality")) return "info";
  return "muted";
}

const countries: Record<string, string> = {
  germany: "DE", deutschland: "DE", austria: "AT", china: "CN", india: "IN", japan: "JP",
  france: "FR", italy: "IT", spain: "ES", poland: "PL", turkey: "TR", türkiye: "TR",
  "united kingdom": "GB", uk: "GB", "united states": "US", usa: "US", switzerland: "CH",
  netherlands: "NL", belgium: "BE", sweden: "SE", denmark: "DK", finland: "FI", norway: "NO",
  czechia: "CZ", "czech republic": "CZ", portugal: "PT", romania: "RO", hungary: "HU",
  vietnam: "VN", taiwan: "TW", "south korea": "KR", brazil: "BR", mexico: "MX", canada: "CA",
};
export function countryFlag(country: string | null | undefined): string {
  if (!country?.trim()) return "-";
  const value = country.trim();
  const code = countries[value.toLowerCase()] ?? (/^[A-Za-z]{2}$/.test(value) ? value.toUpperCase() : null);
  return code ? [...code].map((c) => String.fromCodePoint(127397 + c.charCodeAt(0))).join("") : value;
}

/** Visual coordinates only: descending stored euro values, never a cost or score calculation. */
export function costPositions(values: (number | null | undefined)[]): (number | null)[] {
  const finite = values.filter((v): v is number => v != null && Number.isFinite(v));
  if (!finite.length) return values.map(() => null);
  const high = Math.max(...finite);
  const low = Math.min(...finite);
  return values.map((v) => v == null || !Number.isFinite(v) ? null : high === low ? 0 : (high - v) / (high - low) * 100);
}