import { describe, expect, it } from "vitest";
import { envelopeScore } from "./command";

describe("envelopeScore", () => {
  it("matches the Brandlhuber session score of 0.525", () => {
    expect(envelopeScore(142000, 131500, 122000)).toBeCloseTo(0.525, 3);
  });
  it("is 0 at the opening price and 1 at the best floor", () => {
    expect(envelopeScore(100, 100, 80)).toBe(0);
    expect(envelopeScore(100, 80, 80)).toBe(1);
  });
});
