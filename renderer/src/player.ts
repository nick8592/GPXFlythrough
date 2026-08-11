import type { TrackRenderPayload } from "./types/track.js";
import type { FollowCamera } from "./camera.js";

export class Player {
  private readonly camera: FollowCamera;
  private readonly durationMs: number;
  private readonly fps: number;

  constructor(payload: TrackRenderPayload, camera: FollowCamera, overrideDurationS?: number) {
    this.camera = camera;
    this.fps = payload.render.fps;
    const trackDurationMs = camera.getDurationMs();
    if (overrideDurationS !== undefined && overrideDurationS > 0) {
      this.durationMs = Math.min(overrideDurationS * 1000, trackDurationMs);
    } else {
      this.durationMs = trackDurationMs;
    }
  }

  seek(ms: number): void {
    const clamped = Math.max(0, Math.min(ms, this.durationMs));
    this.camera.seek(clamped);
  }

  getTotalFrames(): number {
    return Math.floor((this.durationMs * this.fps) / 1000);
  }

  getDurationMs(): number {
    return this.durationMs;
  }
}
