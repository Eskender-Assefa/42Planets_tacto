import { describe, expect, it } from "vitest";
import { costPositions, countryFlag, latencyLabel, velocityLabel, protocolTone } from "@/lib/telemetry";

describe("Telemetry presentation rules", () => {
  it("positions stored costs without deriving a score", () => {
    expect(costPositions([150000, 136500, 122000, 120000])).toEqual([0, 45, 28000 / 30000 * 100, 100]);
  });
  it("omits missing markers while preserving zero costs", () => {
    expect(costPositions([null, undefined, 0, 100])).toEqual([null, null, 100, 0]);
  });
  it("handles equal costs without non-finite positions", () => {
    expect(costPositions([122000, 122000, null])).toEqual([0, 0, null]);
  });
  it("converts stored latency to seconds", () => {
    expect(latencyLabel(6200)).toBe("6.2 s");
    expect(latencyLabel(null)).toBe("-");
  });
  it("formats concession velocity as percent per round", () => {
    expect(velocityLabel(0.004)).toBe("0.40% of C_open / round");
  });
  it("assigns the requested protocol families", () => {
    expect(protocolTone("Leverage - Aggressive Protocol")).toBe("success");
    expect(protocolTone("Strategic - Safeguard Protocol")).toBe("warning");
    expect(protocolTone("Bottleneck - Protection Protocol")).toBe("warning");
    expect(protocolTone("Quality Escalation Protocol")).toBe("info");
    expect(protocolTone("Routine - Efficiency Protocol")).toBe("muted");
  });
  it("supports full country names and ISO country codes", () => {
    expect(countryFlag("Germany")).toBe("🇩🇪");
    expect(countryFlag("DE")).toBe("🇩🇪");
    expect(countryFlag(null)).toBe("-");
  });
});