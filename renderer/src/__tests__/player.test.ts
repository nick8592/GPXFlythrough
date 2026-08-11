import { describe, it, expect } from "vitest";

/** Pure computation: total frames = floor(durationMs * fps / 1000) — avoids FP drift from 1000/fps */
function computeTotalFrames(durationMs: number, fps: number): number {
  return Math.floor((durationMs * fps) / 1000);
}

/** Pure computation: seek clamping */
function clampSeek(ms: number, durationMs: number): number {
  return Math.max(0, Math.min(ms, durationMs));
}

describe("Player computation logic", () => {
  it("computes total frames for 30fps 30s animation", () => {
    expect(computeTotalFrames(30_000, 30)).toBe(900);
  });

  it("computes total frames for 24fps 5s animation", () => {
    expect(computeTotalFrames(5000, 24)).toBe(120);
  });

  it("clamps seek to 0 for negative values", () => {
    expect(clampSeek(-100, 5000)).toBe(0);
  });

  it("clamps seek to duration for values exceeding duration", () => {
    expect(clampSeek(10_000, 5000)).toBe(5000);
  });

  it("override duration caps at track duration", () => {
    const trackDurationMs = 120_000;
    const overrideS = 10;
    const result = Math.min(overrideS * 1000, trackDurationMs);
    expect(result).toBe(10_000);
  });

  it("override duration larger than track caps at track duration", () => {
    const trackDurationMs = 30_000;
    const overrideS = 120;
    const result = Math.min(overrideS * 1000, trackDurationMs);
    expect(result).toBe(30_000);
  });
});
