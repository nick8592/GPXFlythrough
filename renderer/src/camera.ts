/** Follow camera — positions camera along the track path. */
import type { TrackRenderPayload, Point } from "./types/track.js";
import type { CameraController } from "./controller.js";

export class FollowCamera implements CameraController {
  private readonly viewer: Cesium.Viewer;
  private readonly payload: TrackRenderPayload;
  private readonly heightAboveTerrain: number;
  private readonly pitchDeg: number;

  constructor(viewer: Cesium.Viewer, payload: TrackRenderPayload) {
    this.viewer = viewer;
    this.payload = payload;
    const cam = payload.render.camera;
    this.heightAboveTerrain = cam.height_above_terrain_m;
    this.pitchDeg = cam.pitch_deg;
  }

  /** Position camera at a specific point along the track, looking ahead. */
  seek(progressMs: number): void {
    const point = this.getPointAtTime(progressMs);
    if (point === null) return;

    const nextPoint = this.getLookaheadPoint(progressMs);

    const altitude = (point.ele ?? 0) + this.heightAboveTerrain;
    const destination = Cesium.Cartesian3.fromDegrees(
      point.lon,
      point.lat,
      altitude,
    );

    if (nextPoint !== null) {
      const nextAlt = (nextPoint.ele ?? 0) + this.heightAboveTerrain;
      const lookTarget = Cesium.Cartesian3.fromDegrees(
        nextPoint.lon,
        nextPoint.lat,
        nextAlt,
      );

      this.viewer.camera.setView({
        destination,
        orientation: {
          direction: Cesium.Cartesian3.subtract(
            lookTarget,
            destination,
            new Cesium.Cartesian3(),
          ),
          up: Cesium.Cartesian3.UNIT_Z,
        },
      });
    } else {
      // Last point — just position camera with fixed orientation
      this.viewer.camera.setView({
        destination,
        orientation: {
          heading: 0,
          pitch: Cesium.CesiumMath.toRadians(this.pitchDeg),
          roll: 0,
        },
      });
    }
  }

  /** Find the track point closest to the given time (ms from start). */
  private getPointAtTime(timeMs: number): Point | null {
    const timeS = timeMs / 1000;
    let elapsedS = 0;
    const segments = this.payload.track.segments;
    const lastSegment = segments[segments.length - 1];

    for (const segment of segments) {
      const isLast = segment === lastSegment;
      if (timeS <= elapsedS + segment.duration_s || isLast) {
        const segTimeS = timeS - elapsedS;
        const fraction =
          segment.duration_s > 0
            ? segTimeS / segment.duration_s
            : 0;
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

  /** Find a point slightly ahead of the current position for camera direction. */
  private getLookaheadPoint(timeMs: number): Point | null {
    // Advance by 2% of total duration, minimum 1 second
    const advanceMs = Math.max(this.getDurationMs() * 0.02, 1000);
    return this.getPointAtTime(
      Math.min(timeMs + advanceMs, this.getDurationMs()),
    );
  }

  /** Get total duration in milliseconds across all segments. */
  getDurationMs(): number {
    return this.payload.track.segments.reduce(
      (sum, seg) => sum + seg.duration_s * 1000,
      0,
    );
  }
}
