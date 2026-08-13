import type { TrackRenderPayload, SchemaVersion } from "../types/track.js";

const SCHEMA_VERSION: SchemaVersion = "1.0.0";

/** Validate a raw parsed JSON value as a TrackRenderPayload. Throws on invalid input. */
export function validate(input: unknown): TrackRenderPayload {
  if (typeof input !== "object" || input === null) {
    throw new Error("invalid payload: expected object");
  }
  const obj = input as Record<string, unknown>;

  // schema_version
  if (obj.schema_version !== SCHEMA_VERSION) {
    throw new Error(`invalid payload: schema_version must be "${SCHEMA_VERSION}", got "${String(obj.schema_version)}"`);
  }

  // track
  if (typeof obj.track !== "object" || obj.track === null) {
    throw new Error("invalid payload: track must be an object");
  }
  const track = obj.track as Record<string, unknown>;

  if (typeof track.name !== "string") {
    throw new Error("invalid payload: track.name must be a string");
  }
  if (!Array.isArray(track.segments)) {
    throw new Error("invalid payload: track.segments must be an array");
  }
  if (!Array.isArray(track.waypoints)) {
    throw new Error("invalid payload: track.waypoints must be an array");
  }

  // bounds
  if (typeof track.bounds !== "object" || track.bounds === null) {
    throw new Error("invalid payload: track.bounds must be an object");
  }

  // segments
  const segments = track.segments as unknown[];
  for (let si = 0; si < segments.length; si++) {
    const seg = segments[si] as Record<string, unknown>;
    if (!Array.isArray(seg.points)) {
      throw new Error(`invalid payload: segment[${si}].points must be an array`);
    }
    const points = seg.points as unknown[];
    for (let pi = 0; pi < points.length; pi++) {
      validatePoint(points[pi] as Record<string, unknown>, si, pi);
    }
  }

  // render
  if (typeof obj.render !== "object" || obj.render === null) {
    throw new Error("invalid payload: render must be an object");
  }
  const render = obj.render as Record<string, unknown>;
  if (typeof render.fps !== "number") {
    throw new Error("invalid payload: render.fps must be a number");
  }

  return input as TrackRenderPayload;
}

function validatePoint(pt: Record<string, unknown>, segIdx: number, ptIdx: number): void {
  if (typeof pt.lat !== "number" || pt.lat < -90 || pt.lat > 90) {
    throw new Error(`invalid payload: segment[${segIdx}].points[${ptIdx}].lat must be in [-90, 90], got ${String(pt.lat)}`);
  }
  if (typeof pt.lon !== "number" || pt.lon < -180 || pt.lon > 180) {
    throw new Error(`invalid payload: segment[${segIdx}].points[${ptIdx}].lon must be in [-180, 180], got ${String(pt.lon)}`);
  }
  if (pt.ele !== null && typeof pt.ele !== "number") {
    throw new Error(`invalid payload: segment[${segIdx}].points[${ptIdx}].ele must be number or null`);
  }
  if (typeof pt.cumulative_m !== "number" || pt.cumulative_m < 0) {
    throw new Error(`invalid payload: segment[${segIdx}].points[${ptIdx}].cumulative_m must be non-negative number, got ${String(pt.cumulative_m)}`);
  }
}
