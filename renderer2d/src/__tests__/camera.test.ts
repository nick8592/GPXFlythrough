import { describe, it, expect, vi } from "vitest";
import type { Map as MapLibreMap, ExpressionSpecification } from "maplibre-gl";
import type { TrackRenderPayload } from "../types/track.js";
import { getPointAtTime, MapCamera } from "../camera.js";

function createMockMap(): MapLibreMap {
  return {
    jumpTo: vi.fn(),
    setPaintProperty: vi.fn(),
    on: vi.fn(),
  } as unknown as MapLibreMap;
}

const singleSegmentPayload: TrackRenderPayload = {
  schema_version: "1.0.0",
  track: {
    name: "Test",
    activity_type: null,
    bounds: {
      min_lat: 25.033,
      max_lat: 25.035,
      min_lon: 121.565,
      max_lon: 121.567,
      min_ele: 120,
      max_ele: 140,
    },
    segments: [
      {
        index: 0,
        start_time_iso: null,
        duration_s: 120,
        length_m: 1000,
        points: [
          { lat: 25.033, lon: 121.565, ele: 120, time: null, cumulative_m: 0, speed: null, hr: null, cad: null, temp: null },
          { lat: 25.034, lon: 121.566, ele: 130, time: null, cumulative_m: 500, speed: null, hr: null, cad: null, temp: null },
          { lat: 25.035, lon: 121.567, ele: 140, time: null, cumulative_m: 1000, speed: null, hr: null, cad: null, temp: null },
        ],
      },
    ],
    waypoints: [],
  },
  render: {
    fps: 30,
    resolution: { label: "1080p", width: 1920, height: 1080 },
    camera: { mode: "follow", height_above_terrain_m: 50, lookahead_m: 100, pitch_deg: -15 },
    theme: "dark",
    overlays: [],
    no_terrain: true,
  },
};

const multiSegmentPayload: TrackRenderPayload = {
  schema_version: "1.0.0",
  track: {
    name: "Multi",
    activity_type: null,
    bounds: {
      min_lat: 25.033,
      max_lat: 25.037,
      min_lon: 121.565,
      max_lon: 121.569,
      min_ele: 120,
      max_ele: 160,
    },
    segments: [
      {
        index: 0,
        start_time_iso: null,
        duration_s: 60,
        length_m: 500,
        points: [
          { lat: 25.033, lon: 121.565, ele: 120, time: null, cumulative_m: 0, speed: null, hr: null, cad: null, temp: null },
          { lat: 25.034, lon: 121.566, ele: 130, time: null, cumulative_m: 250, speed: null, hr: null, cad: null, temp: null },
          { lat: 25.035, lon: 121.567, ele: 140, time: null, cumulative_m: 500, speed: null, hr: null, cad: null, temp: null },
        ],
      },
      {
        index: 1,
        start_time_iso: null,
        duration_s: 60,
        length_m: 500,
        points: [
          { lat: 25.035, lon: 121.567, ele: 140, time: null, cumulative_m: 500, speed: null, hr: null, cad: null, temp: null },
          { lat: 25.036, lon: 121.568, ele: 150, time: null, cumulative_m: 750, speed: null, hr: null, cad: null, temp: null },
          { lat: 25.037, lon: 121.569, ele: 160, time: null, cumulative_m: 1000, speed: null, hr: null, cad: null, temp: null },
        ],
      },
    ],
    waypoints: [],
  },
  render: {
    fps: 30,
    resolution: { label: "1080p", width: 1920, height: 1080 },
    camera: { mode: "follow", height_above_terrain_m: 50, lookahead_m: 100, pitch_deg: -15 },
    theme: "dark",
    overlays: [],
    no_terrain: true,
  },
};

/**
 * Extract the per-segment gradient stop at `progressFraction` for a given
 * `setPaintProperty` mock call. The line-gradient expression shape is:
 *   ["interpolate", ["linear"], ["line-progress"],
 *    0, drawnColor, pf, drawnColor, pf, undrawnColor, 1, undrawnColor]
 * The `pf` stop pairs occur at indices 5 and 7 of the flat array.
 */
function extractProgressFraction(callArgs: unknown[]): number {
  const gradient = callArgs[2] as ExpressionSpecification | undefined;
  if (!Array.isArray(gradient)) {
    throw new Error("gradient is not an array");
  }
  // The two progress-fraction stop values are at flat indices 5 and 7.
  const pf1 = gradient[5] as unknown;
  const pf2 = gradient[7] as unknown;
  if (typeof pf1 !== "number" || typeof pf2 !== "number") {
    throw new Error(`expected numeric stops at indices 5, 7; got ${typeof pf1}, ${typeof pf2}`);
  }
  if (pf1 !== pf2) {
    throw new Error(`stop pair at 5, 7 should be equal; got ${pf1}, ${pf2}`);
  }
  return pf1;
}

describe("MapCamera", () => {
  it("computes total duration from segments", () => {
    const camera = new MapCamera(createMockMap(), singleSegmentPayload);
    expect(camera.getDurationMs()).toBe(120_000);
  });

  it("computes total duration across multiple segments", () => {
    const camera = new MapCamera(createMockMap(), multiSegmentPayload);
    expect(camera.getDurationMs()).toBe(120_000);
  });

  it("seek(0) jumps to first track point", () => {
    const map = createMockMap();
    const camera = new MapCamera(map, singleSegmentPayload);
    camera.seek(0);
    expect(map.jumpTo).toHaveBeenCalledWith({ center: [121.565, 25.033] });
  });

  it("seek(ms) calls jumpTo with midpoint coordinates", () => {
    const map = createMockMap();
    const camera = new MapCamera(map, singleSegmentPayload);
    camera.seek(60_000);
    expect(map.jumpTo).toHaveBeenCalledWith({ center: [121.566, 25.034] });
  });

  it("seek(ms) calls setPaintProperty for the segment layer", () => {
    const map = createMockMap();
    const camera = new MapCamera(map, singleSegmentPayload);
    camera.seek(0);
    const calls = (map.setPaintProperty as ReturnType<typeof vi.fn>).mock.calls;
    const segmentCall = calls.find((c) => c[0] === "segment-0-line");
    expect(segmentCall).toBeDefined();
    expect(segmentCall?.[1]).toBe("line-gradient");
  });

  it("seek(0) sets line-gradient progressFraction to 0 (fully undrawn)", () => {
    const map = createMockMap();
    const camera = new MapCamera(map, singleSegmentPayload);
    camera.seek(0);
    const calls = (map.setPaintProperty as ReturnType<typeof vi.fn>).mock.calls;
    const segmentCall = calls.find((c) => c[0] === "segment-0-line");
    expect(extractProgressFraction(segmentCall ?? [])).toBe(0);
  });

  it("seek at midpoint sets line-gradient progressFraction to 0.5", () => {
    const map = createMockMap();
    const camera = new MapCamera(map, singleSegmentPayload);
    camera.seek(60_000);
    const calls = (map.setPaintProperty as ReturnType<typeof vi.fn>).mock.calls;
    const segmentCall = calls.find((c) => c[0] === "segment-0-line");
    expect(extractProgressFraction(segmentCall ?? [])).toBeCloseTo(0.5);
  });

  it("seek at full duration sets line-gradient progressFraction to 1 (fully drawn)", () => {
    const map = createMockMap();
    const camera = new MapCamera(map, singleSegmentPayload);
    camera.seek(120_000);
    const calls = (map.setPaintProperty as ReturnType<typeof vi.fn>).mock.calls;
    const segmentCall = calls.find((c) => c[0] === "segment-0-line");
    expect(extractProgressFraction(segmentCall ?? [])).toBe(1);
  });

  it("multi-segment: first segment fully drawn after its duration", () => {
    const map = createMockMap();
    const camera = new MapCamera(map, multiSegmentPayload);
    camera.seek(60_000); // end of segment 0
    const calls = (map.setPaintProperty as ReturnType<typeof vi.fn>).mock.calls;
    const seg0 = calls.find((c) => c[0] === "segment-0-line");
    const seg1 = calls.find((c) => c[0] === "segment-1-line");
    expect(extractProgressFraction(seg0 ?? [])).toBe(1);
    expect(extractProgressFraction(seg1 ?? [])).toBe(0);
  });

  it("multi-segment: second segment partially drawn mid-playback", () => {
    const map = createMockMap();
    const camera = new MapCamera(map, multiSegmentPayload);
    // Segment 0 is 0-60s, segment 1 is 60-120s. At 90s, seg 1 is at 0.5.
    camera.seek(90_000);
    const calls = (map.setPaintProperty as ReturnType<typeof vi.fn>).mock.calls;
    const seg0 = calls.find((c) => c[0] === "segment-0-line");
    const seg1 = calls.find((c) => c[0] === "segment-1-line");
    expect(extractProgressFraction(seg0 ?? [])).toBe(1);
    expect(extractProgressFraction(seg1 ?? [])).toBeCloseTo(0.5);
  });
});

describe("getPointAtTime", () => {
  it("returns first point at time 0", () => {
    const point = getPointAtTime(singleSegmentPayload.track.segments, 0);
    expect(point).not.toBeNull();
    expect(point?.lat).toBe(25.033);
    expect(point?.lon).toBe(121.565);
  });

  it("returns last point at end of track duration", () => {
    const point = getPointAtTime(singleSegmentPayload.track.segments, 120_000);
    expect(point).not.toBeNull();
    expect(point?.lat).toBe(25.035);
    expect(point?.lon).toBe(121.567);
  });

  it("returns midpoint around half duration", () => {
    const point = getPointAtTime(singleSegmentPayload.track.segments, 60_000);
    expect(point).not.toBeNull();
    expect(point?.lat).toBe(25.034);
  });

  it("returns null for empty segments", () => {
    expect(getPointAtTime([], 1000)).toBeNull();
  });
});
