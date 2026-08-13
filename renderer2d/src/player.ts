import type { CameraController } from "./controller.js";

export type PlayerState = "idle" | "playing" | "paused" | "finished";

export interface RafProvider {
  requestAnimationFrame(cb: (timestamp: number) => void): number;
  cancelAnimationFrame(id: number): void;
}

export class Player {
  private readonly controller: CameraController;
  readonly durationMs: number;

  private readonly raf: RafProvider;

  private _state: PlayerState = "idle";
  private _currentTimeMs = 0;
  private _speed = 1;

  private rafId: number | null = null;
  private lastFrameTime: number | null = null;

  private readonly tickSubs: Array<(ms: number) => void> = [];
  private readonly stateSubs: Array<(s: PlayerState) => void> = [];

  constructor(controller: CameraController, durationMs: number, raf?: RafProvider) {
    this.controller = controller;
    this.durationMs = durationMs;
    this.raf = raf ?? {
      requestAnimationFrame: (cb) => globalThis.requestAnimationFrame(cb),
      cancelAnimationFrame: (id) => globalThis.cancelAnimationFrame(id),
    };
  }

  get state(): PlayerState {
    return this._state;
  }

  get currentTimeMs(): number {
    return this._currentTimeMs;
  }

  get speed(): number {
    return this._speed;
  }

  play(): void {
    if (this._state === "playing") return;

    if (this._state === "finished") {
      this._currentTimeMs = 0;
    }

    this.setState("playing");
    this.lastFrameTime = null;
    this.scheduleFrame();
  }

  pause(): void {
    if (this._state !== "playing") return;
    this.cancelFrame();
    this.setState("paused");
  }

  togglePlay(): void {
    if (this._state === "playing") {
      this.pause();
    } else {
      this.play();
    }
  }

  seek(ms: number): void {
    this._currentTimeMs = Math.max(0, Math.min(ms, this.durationMs));
    this.controller.seek(this._currentTimeMs);
    this.notifyTick();
  }

  setSpeed(multiplier: number): void {
    this._speed = multiplier;
  }

  onTick(cb: (ms: number) => void): () => void {
    this.tickSubs.push(cb);
    return () => {
      const idx = this.tickSubs.indexOf(cb);
      if (idx !== -1) this.tickSubs.splice(idx, 1);
    };
  }

  onStateChange(cb: (s: PlayerState) => void): () => void {
    this.stateSubs.push(cb);
    return () => {
      const idx = this.stateSubs.indexOf(cb);
      if (idx !== -1) this.stateSubs.splice(idx, 1);
    };
  }

  dispose(): void {
    this.cancelFrame();
    this.tickSubs.length = 0;
    this.stateSubs.length = 0;
  }

  private setState(next: PlayerState): void {
    if (this._state === next) return;
    this._state = next;
    for (const cb of this.stateSubs) cb(next);
  }

  private scheduleFrame(): void {
    this.rafId = this.raf.requestAnimationFrame(this.onFrame);
  }

  private cancelFrame(): void {
    if (this.rafId !== null) {
      this.raf.cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }

  private readonly onFrame = (timestamp: number): void => {
    if (this._state !== "playing") return;

    if (this.lastFrameTime !== null) {
      const deltaMs = (timestamp - this.lastFrameTime) * this._speed;
      this._currentTimeMs += deltaMs;
    }

    this.lastFrameTime = timestamp;

    if (this._currentTimeMs >= this.durationMs) {
      this._currentTimeMs = this.durationMs;
      this.controller.seek(this._currentTimeMs);
      this.notifyTick();
      this.cancelFrame();
      this.setState("finished");
      return;
    }

    this.controller.seek(this._currentTimeMs);
    this.notifyTick();
    this.scheduleFrame();
  };

  private notifyTick(): void {
    for (const cb of this.tickSubs) cb(this._currentTimeMs);
  }
}
