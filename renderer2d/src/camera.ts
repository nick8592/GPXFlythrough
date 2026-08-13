/** MapCamera — MapLibre-based 2D camera with track drawing animation. */
import type { Map as MapLibreMap, ExpressionSpecification } from "maplibre-gl";
import type { TrackRenderPayload, Point } from "./types/track.js";
import type { CameraController } from "./controller.js";

/** Find the track point closest to the given time (ms from start). */
export function getPointAtTime(
  segments: TrackRenderPayload["track"]["segments"],
  timeMs: number,
): Point | null {
  const timeS = timeMs / 1000;
  let elapsedS = 0;
  const lastSegment = segments[segments.length - 1];

  for (const segment of segments) {
    const isLast = segment === lastSegment;
    if (timeS <= elapsedS + segment.duration_s || isLast) {
      const segTimeS = timeS - elapsedS;
      const fraction =
        segment.duration_s > 0 ? segTimeS / segment.duration_s : 0;
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

/** Color used for the "drawn" portion of each segment. */
const DRAWN_COLOR = "#FFD700";
/** Color used for the "undrawn" portion of each segment. */
const UNDRAWN_COLOR = "rgba(255,255,255,0.15)";

/** Layer ID for segment at index i. */
function segmentLayerId(i: number): string {
  return `segment-${i}-line`;
}

/**
 * Build a `line-gradient` expression that draws the segment up to
 * `progressFraction` (0-1) in DRAWN_COLOR, the rest in UNDRAWN_COLOR.
 *
 * Uses MapLibre's `interpolate-linear` with duplicate stops at
 * `progressFraction` to produce a sharp transition.
 */
function buildLineGradient(progressFraction: number): ExpressionSpecification {
  const pf = Math.max(0, Math.min(1, progressFraction));
  return [
    "interpolate",
    ["linear"],
    ["line-progress"],
    0,
    DRAWN_COLOR,
    pf,
    DRAWN_COLOR,
    pf,
    UNDRAWN_COLOR,
    1,
    UNDRAWN_COLOR,
  ];
}

interface SegmentTiming {
  startMs: number;
  endMs: number;
}

export class MapCamera implements CameraController {
  private readonly map: MapLibreMap;
  private readonly payload: TrackRenderPayload;
  private readonly segmentTimings: SegmentTiming[];

  constructor(map: MapLibreMap, payload: TrackRenderPayload) {
    this.map = map;
    this.payload = payload;

    // Precompute cumulative start/end times for each segment.
    let elapsedMs = 0;
    this.segmentTimings = payload.track.segments.map((seg) => {
      const durMs = seg.duration_s * 1000;
      const timing: SegmentTiming = { startMs: elapsedMs, endMs: elapsedMs + durMs };
      elapsedMs += durMs;
      return timing;
    });
  }

  getDurationMs(): number {
    return this.payload.track.segments.reduce(
      (sum, seg) => sum + seg.duration_s * 1000,
      0,
    );
  }

  seek(progressMs: number): void {
    const point = getPointAtTime(this.payload.track.segments, progressMs);

    // 1. Pan map to center on current point.
    if (point !== null) {
      this.map.jumpTo({ center: [point.lon, point.lat] });
    }

    // 2. Update drawing animation per segment.
    for (let i = 0; i < this.segmentTimings.length; i++) {
      const timing = this.segmentTimings[i];
      if (timing === undefined) continue;

      let segFraction: number;
      if (progressMs <= timing.startMs) {
        segFraction = 0;
      } else if (progressMs >= timing.endMs) {
        segFraction = 1;
      } else {
        const segSpan = timing.endMs - timing.startMs;
        segFraction = segSpan > 0 ? (progressMs - timing.startMs) / segSpan : 0;
      }

      const layerId = segmentLayerId(i);
      this.map.setPaintProperty(layerId, "line-gradient", buildLineGradient(segFraction));
    }
  }
}
