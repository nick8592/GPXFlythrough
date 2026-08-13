/** Follow camera — positions camera along the track path. */
import type { TrackRenderPayload, Point } from "./types/track.js";
import type { CameraController } from "./controller.js";

/** Minimum squared distance (m²) between camera and lookahead for a valid direction. */
const MIN_DIRECTION_DIST_SQ = 1.0;

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

export class FollowCamera implements CameraController {
  private readonly viewer: Cesium.Viewer;
  private readonly payload: TrackRenderPayload;
  private readonly heightAboveTerrain: number;
  private readonly pitchDeg: number;
  private readonly lookaheadMs: number;
  private lastValidHeading: number | null = null;

  constructor(viewer: Cesium.Viewer, payload: TrackRenderPayload) {
    this.viewer = viewer;
    this.payload = payload;
    const cam = payload.render.camera;
    this.heightAboveTerrain = cam.height_above_terrain_m;
    this.pitchDeg = cam.pitch_deg;
    this.lookaheadMs = Math.max(
      this.getDurationMs() * 0.02,
      1000,
    );
  }

  seek(progressMs: number): void {
    const point = getPointAtTime(this.payload.track.segments, progressMs);
    if (point === null) return;

    const altitude = (point.ele ?? 0) + this.heightAboveTerrain;
    const destination = Cesium.Cartesian3.fromDegrees(
      point.lon,
      point.lat,
      altitude,
    );

    const lookTarget = this.getLookaheadTarget(progressMs, destination);

    if (lookTarget !== null) {
      const direction = Cesium.Cartesian3.normalize(
        Cesium.Cartesian3.subtract(
          lookTarget,
          destination,
          new Cesium.Cartesian3(),
        ),
        new Cesium.Cartesian3(),
      );

      const enuFrame = Cesium.Transforms.eastNorthUpToFixedFrame(destination);
      const up = Cesium.Matrix4.getColumn(enuFrame, 2, new Cesium.Cartesian3());

      this.viewer.camera.setView({
        destination,
        orientation: {
          direction,
          up,
        },
      });

      this.lastValidHeading = this.computeHeading(direction, enuFrame);
    } else {
      this.viewer.camera.setView({
        destination,
        orientation: {
          heading: this.lastValidHeading ?? 0,
          pitch: Cesium.CesiumMath.toRadians(this.pitchDeg),
          roll: 0,
        },
      });
    }
  }

  private getLookaheadTarget(
    progressMs: number,
    destination: Cesium.Cartesian3,
  ): Cesium.Cartesian3 | null {
    const baseMs = Math.min(progressMs + this.lookaheadMs, this.getDurationMs());
    const basePoint = getPointAtTime(this.payload.track.segments, baseMs);
    if (basePoint === null) return null;

    const candidate = this.makeCartesian(basePoint);
    if (this.isFarEnough(candidate, destination)) return candidate;

    return this.scanForward(baseMs, destination);
  }

  private scanForward(
    startMs: number,
    destination: Cesium.Cartesian3,
  ): Cesium.Cartesian3 | null {
    const stepMs = 2000;
    let ms = startMs + stepMs;
    const limit = this.getDurationMs();

    while (ms <= limit) {
      const pt = getPointAtTime(this.payload.track.segments, ms);
      if (pt === null) break;
      const candidate = this.makeCartesian(pt);
      if (this.isFarEnough(candidate, destination)) return candidate;
      ms += stepMs;
    }

    return null;
  }

  private makeCartesian(pt: Point): Cesium.Cartesian3 {
    return Cesium.Cartesian3.fromDegrees(
      pt.lon,
      pt.lat,
      (pt.ele ?? 0) + this.heightAboveTerrain,
    );
  }

  private isFarEnough(
    candidate: Cesium.Cartesian3,
    destination: Cesium.Cartesian3,
  ): boolean {
    const diff = Cesium.Cartesian3.subtract(
      candidate,
      destination,
      new Cesium.Cartesian3(),
    );
    return Cesium.Cartesian3.magnitudeSquared(diff) > MIN_DIRECTION_DIST_SQ;
  }

  private computeHeading(
    direction: Cesium.Cartesian3,
    enuFrame: Cesium.Matrix4,
  ): number {
    const east = Cesium.Matrix4.getColumn(enuFrame, 0, new Cesium.Cartesian3());
    const north = Cesium.Matrix4.getColumn(enuFrame, 1, new Cesium.Cartesian3());
    const dEast = Cesium.Cartesian3.dot(direction, east);
    const dNorth = Cesium.Cartesian3.dot(direction, north);
    return Math.atan2(dEast, dNorth);
  }

  getDurationMs(): number {
    return this.payload.track.segments.reduce(
      (sum, seg) => sum + seg.duration_s * 1000,
      0,
    );
  }
}
