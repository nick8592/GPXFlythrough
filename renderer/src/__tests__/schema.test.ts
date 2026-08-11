import { describe, it, expect } from "vitest";
import { validate } from "../schema/track-render.js";
import payloadMinimal from "./fixtures/payload-minimal.json" with { type: "json" };

describe("TrackRenderPayload validator", () => {
  it("accepts the minimal payload fixture", () => {
    const result = validate(payloadMinimal);
    expect(result.schema_version).toBe("1.0.0");
    expect(result.track.segments).toHaveLength(1);
    expect(result.track.segments[0].points).toHaveLength(3);
  });

  it("rejects wrong schema_version", () => {
    const bad = { ...payloadMinimal, schema_version: "0.9.0" };
    expect(() => validate(bad)).toThrow("schema_version");
  });

  it("rejects point with lat out of range", () => {
    const bad = structuredClone(payloadMinimal);
    const track = bad.track as { segments: { points: { lat: number }[] }[] };
    track.segments[0].points[0].lat = 95;
    expect(() => validate(bad)).toThrow("lat");
  });

  it("rejects negative cumulative_m", () => {
    const bad = structuredClone(payloadMinimal);
    const track = bad.track as { segments: { points: { cumulative_m: number }[] }[] };
    track.segments[0].points[0].cumulative_m = -1;
    expect(() => validate(bad)).toThrow("cumulative_m");
  });

  it("rejects missing segments array", () => {
    const bad = { ...payloadMinimal };
    (bad as Record<string, unknown>).track = { ...(bad.track as object), segments: null };
    expect(() => validate(bad)).toThrow("segments");
  });

  it("rejects non-object input", () => {
    expect(() => validate(null)).toThrow("expected object");
    expect(() => validate(42)).toThrow("expected object");
    expect(() => validate("string")).toThrow("expected object");
  });

  it("rejects missing render section", () => {
    const bad = { ...payloadMinimal, render: null };
    expect(() => validate(bad)).toThrow("render");
  });

  it("rejects non-number fps", () => {
    const bad = { ...payloadMinimal, render: { ...(payloadMinimal.render as object), fps: "thirty" } };
    expect(() => validate(bad)).toThrow("fps");
  });
});
