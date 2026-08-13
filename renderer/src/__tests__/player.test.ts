import { describe, it, expect, vi, afterEach } from "vitest";
import type { CameraController } from "../controller.js";
import { Player } from "../player.js";
import type { PlayerState } from "../player.js";
import type { RafProvider } from "../player.js";

function createMockController(durationMs: number): CameraController {
  return {
    seek: vi.fn(),
    getDurationMs: vi.fn(() => durationMs),
  };
}

/**
 * Fake requestAnimationFrame provider for testing.
 * Stores scheduled callbacks; `flushFrames` invokes them in order
 * with timestamps that increment by `frameDeltaMs` per frame.
 */
function createFakeRaf(frameDeltaMs = 16): RafProvider & {
  flushFrames(count: number): void;
  pendingCount(): number;
} {
  const queue: Array<{ cb: (timestamp: number) => void; id: number }> = [];
  let nextId = 1;
  let currentTime = 0;

  return {
    requestAnimationFrame(cb: (timestamp: number) => void): number {
      const id = nextId++;
      queue.push({ cb, id });
      return id;
    },
    cancelAnimationFrame(id: number): void {
      const idx = queue.findIndex((entry) => entry.id === id);
      if (idx !== -1) queue.splice(idx, 1);
    },
    flushFrames(count: number): void {
      for (let i = 0; i < count; i++) {
        if (queue.length === 0) break;
        currentTime += frameDeltaMs;
        const entry = queue.shift();
        if (entry) entry.cb(currentTime);
      }
    },
    pendingCount(): number {
      return queue.length;
    },
  };
}

describe("Player", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("initial state is idle, currentTimeMs === 0, speed === 1", () => {
    const controller = createMockController(10_000);
    const raf = createFakeRaf();
    const player = new Player(controller, 10_000, raf);

    expect(player.state).toBe("idle");
    expect(player.currentTimeMs).toBe(0);
    expect(player.speed).toBe(1);
  });

  it("play() transitions to playing; pause() to paused; play() again resumes", () => {
    const controller = createMockController(10_000);
    const raf = createFakeRaf();
    const player = new Player(controller, 10_000, raf);

    player.play();
    expect(player.state).toBe("playing");

    player.pause();
    expect(player.state).toBe("paused");

    player.play();
    expect(player.state).toBe("playing");
  });

  it("seek(ms) clamps to [0, durationMs]", () => {
    const controller = createMockController(10_000);
    const raf = createFakeRaf();
    const player = new Player(controller, 10_000, raf);

    player.seek(5_000);
    expect(player.currentTimeMs).toBe(5_000);
    expect(controller.seek).toHaveBeenCalledWith(5_000);

    player.seek(-100);
    expect(player.currentTimeMs).toBe(0);

    player.seek(20_000);
    expect(player.currentTimeMs).toBe(10_000);
  });

  it("setSpeed(2) doubles advance rate", () => {
    const controller = createMockController(10_000);
    const raf = createFakeRaf();
    const player = new Player(controller, 10_000, raf);

    player.setSpeed(2);
    player.play();

    // Frame 1: sets lastFrameTime, no delta accumulated
    raf.flushFrames(1);
    // Frame 2: 16ms real time * speed 2 = 32ms track time
    raf.flushFrames(1);

    expect(player.currentTimeMs).toBeGreaterThanOrEqual(30);
    expect(player.currentTimeMs).toBeLessThanOrEqual(34);
  });

  it("reaching durationMs triggers state finished and stops the loop", () => {
    const controller = createMockController(100);
    const raf = createFakeRaf();
    const player = new Player(controller, 100, raf);

    const states: PlayerState[] = [];
    player.onStateChange((s) => states.push(s));

    player.play();

    // 16ms per frame; need enough frames to exceed 100ms
    raf.flushFrames(10);

    expect(player.state).toBe("finished");
    expect(player.currentTimeMs).toBe(100);
    expect(states).toContain("finished");
  });

  it("dispose() cancels rAF and clears subscribers", () => {
    const controller = createMockController(10_000);
    const raf = createFakeRaf();
    const player = new Player(controller, 10_000, raf);

    const tickCb = vi.fn();
    const stateCb = vi.fn();

    player.onTick(tickCb);
    player.onStateChange(stateCb);

    player.play();
    player.dispose();

    // After dispose, no pending frames and no subscribers
    expect(raf.pendingCount()).toBe(0);

    // Flushing should do nothing — no callbacks remain
    raf.flushFrames(5);
    const tickCallCount = tickCb.mock.calls.length;
    const stateCallCount = stateCb.mock.calls.length;

    raf.flushFrames(5);
    expect(tickCb.mock.calls.length).toBe(tickCallCount);
    expect(stateCb.mock.calls.length).toBe(stateCallCount);
  });

  it("subscribers receive ticks at correct cadence", () => {
    const controller = createMockController(10_000);
    const raf = createFakeRaf();
    const player = new Player(controller, 10_000, raf);

    const ticks: number[] = [];
    player.onTick((ms) => ticks.push(ms));

    player.play();

    // Frame 1: sets lastFrameTime, currentTimeMs still 0, tick at 0
    raf.flushFrames(1);
    // Frame 2: 16ms delta, tick at ~16
    raf.flushFrames(1);

    // Should have at least two ticks, with the second being positive
    expect(ticks.length).toBeGreaterThanOrEqual(2);
    expect(ticks[1]).toBeGreaterThan(0);
  });

  it("multiple subscribers all called per tick", () => {
    const controller = createMockController(10_000);
    const raf = createFakeRaf();
    const player = new Player(controller, 10_000, raf);

    const cb1 = vi.fn();
    const cb2 = vi.fn();

    player.onTick(cb1);
    player.onTick(cb2);

    player.seek(5_000);

    expect(cb1).toHaveBeenCalledWith(5_000);
    expect(cb2).toHaveBeenCalledWith(5_000);
  });

  it("unsubscribe removes the callback", () => {
    const controller = createMockController(10_000);
    const raf = createFakeRaf();
    const player = new Player(controller, 10_000, raf);

    const cb = vi.fn();
    const unsub = player.onTick(cb);

    player.seek(1_000);
    expect(cb).toHaveBeenCalledTimes(1);

    unsub();

    player.seek(2_000);
    expect(cb).toHaveBeenCalledTimes(1);
  });

  it("play() from finished resets currentTimeMs to 0", () => {
    const controller = createMockController(50);
    const raf = createFakeRaf();
    const player = new Player(controller, 50, raf);

    player.play();
    raf.flushFrames(10);

    expect(player.state).toBe("finished");
    expect(player.currentTimeMs).toBe(50);

    player.play();
    expect(player.state).toBe("playing");
    expect(player.currentTimeMs).toBe(0);
  });

  it("togglePlay() toggles between playing and paused", () => {
    const controller = createMockController(10_000);
    const raf = createFakeRaf();
    const player = new Player(controller, 10_000, raf);

    expect(player.state).toBe("idle");

    player.togglePlay();
    expect(player.state).toBe("playing");

    player.togglePlay();
    expect(player.state).toBe("paused");

    player.togglePlay();
    expect(player.state).toBe("playing");
  });

  it("onStateChange notifies on each transition", () => {
    const controller = createMockController(10_000);
    const raf = createFakeRaf();
    const player = new Player(controller, 10_000, raf);

    const transitions: PlayerState[] = [];
    player.onStateChange((s) => transitions.push(s));

    player.play();
    player.pause();
    player.play();

    expect(transitions).toEqual(["playing", "paused", "playing"]);
  });

  it("seek calls controller.seek with clamped value", () => {
    const controller = createMockController(10_000);
    const raf = createFakeRaf();
    const player = new Player(controller, 10_000, raf);

    player.seek(3_000);
    expect(controller.seek).toHaveBeenCalledWith(3_000);

    player.seek(15_000);
    expect(controller.seek).toHaveBeenCalledWith(10_000);
  });
});
