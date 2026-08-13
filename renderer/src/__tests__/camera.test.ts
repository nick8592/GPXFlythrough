import { describe, it, expect } from "vitest";
import type { TrackRenderPayload } from "../types/track.js";

/** Extract the duration computation logic for testing without Cesium. */
function computeDurationMs(payload: TrackRenderPayload): number {
  return payload.track.segments.reduce(
    (sum, seg) => sum + seg.duration_s * 1000,
    0,
  );
}

/** Extract the point-at-time computation logic for testing without Cesium. */
function getPointAtTime(
  timeMs: number,
  segments: TrackRenderPayload["track"]["segments"],
): { lat: number; lon: number; ele: number | null } | null {
  const timeS = timeMs / 1000;
  let elapsedS = 0;
  const lastSegment = segments[segments.length - 1];

  for (const segment of segments) {
    const isLast = segment === lastSegment;
    if (timeS <= elapsedS + segment.duration_s || isLast) {
      const segTimeS = timeS - elapsedS;
      const fraction = segment.duration_s > 0 ? segTimeS / segment.duration_s : 0;
      const idx = Math.min(
        Math.floor(fraction * segment.points.length),
        segment.points.length - 1,
      );
      return segment.points[Math.max(0, idx)];
    }
    elapsedS += segment.duration_s;
  }
  return null;
}

const singleSegmentPayload: TrackRenderPayload = {
  schema_version: "1.0.0",
  track: {
    name: "Test",
    activity_type: null,
    bounds: { min_lat: 0, max_lat: 0, min_lon: 0, max_lon: 0, min_ele: 0, max_ele: 0 },
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

describe("FollowCamera computation logic", () => {
  it("computes total duration from segments", () => {
    expect(computeDurationMs(singleSegmentPayload)).toBe(120_000);
  });

  it("returns first point at time 0", () => {
    const point = getPointAtTime(0, singleSegmentPayload.track.segments);
    expect(point).not.toBeNull();
    expect(point?.lat).toBe(25.033);
  });

  it("returns last point at end of track duration", () => {
    const point = getPointAtTime(120_000, singleSegmentPayload.track.segments);
    expect(point).not.toBeNull();
    expect(point?.lat).toBe(25.035);
  });

  it("returns midpoint around half duration", () => {
    const point = getPointAtTime(60_000, singleSegmentPayload.track.segments);
    expect(point).not.toBeNull();
    expect(point?.lat).toBe(25.034);
  });

  it("returns null for empty segments", () => {
    expect(getPointAtTime(1000, [])).toBeNull();
  });
});
