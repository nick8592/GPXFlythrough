import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { Player } from "../player.js";
import { createPlaybackOverlay } from "../ui/playback-overlay.js";

/**
 * Creates a mock Player instance for testing.
 */
function createMockPlayer(durationMs: number = 330000): Player {
  const mockPlayer = {
    _state: "idle",
    _currentTimeMs: 0,
    _speed: 1,
    durationMs,
    play: vi.fn(),
    pause: vi.fn(),
    togglePlay: vi.fn(),
    seek: vi.fn(),
    setSpeed: vi.fn(),
    onTick: vi.fn(() => () => {}),
    onStateChange: vi.fn(() => () => {}),
    dispose: vi.fn(),
  };

  Object.defineProperties(mockPlayer, {
    state: {
      get: function () {
        return this._state;
      },
      configurable: true,
    },
    currentTimeMs: {
      get: function () {
        return this._currentTimeMs;
      },
      configurable: true,
    },
    speed: {
      get: function () {
        return this._speed;
      },
      configurable: true,
    },
  });

  return mockPlayer as unknown as Player;
}

describe("createPlaybackOverlay", () => {
  let container: HTMLElement;
  let player: Player;

  beforeEach(() => {
    player = createMockPlayer(330000); // 5:30
    container = createPlaybackOverlay(player);
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  it("renders play button, progress bar, speed selector, and time labels", () => {
    const playBtn = container.querySelector("button[aria-label='Play']");
    const progressFill = container.querySelector(".playback-overlay__progress-fill");
    const speedBtns = container.querySelectorAll(".playback-overlay__speed-btn");
    const timeLabel = container.querySelector(".playback-overlay__time-label");

    expect(playBtn).toBeTruthy();
    expect(progressFill).toBeTruthy();
    expect(speedBtns.length).toBe(4);
    expect(timeLabel).toBeTruthy();
    expect(timeLabel?.textContent).toBe("0:00 / 5:30");
  });

  it("clicking play button calls player.togglePlay()", () => {
    const playBtn = container.querySelector("button[aria-label='Play']") as HTMLButtonElement;
    playBtn.click();

    expect(player.togglePlay).toHaveBeenCalledTimes(1);
  });

  it("clicking speed option calls player.setSpeed()", () => {
    const speedBtns = container.querySelectorAll(".playback-overlay__speed-btn");
    const speed2xBtn = Array.from(speedBtns).find((btn) => btn.textContent === "2×");

    expect(speed2xBtn).toBeTruthy();
    (speed2xBtn as HTMLButtonElement).click();

    expect(player.setSpeed).toHaveBeenCalledWith(2);
  });

  it("player tick event updates progress bar width and time label", () => {
    let capturedTickCb: ((ms: number) => void) | undefined;
    (player.onTick as ReturnType<typeof vi.fn>).mockImplementation((cb) => {
      capturedTickCb = cb;
      return () => {};
    });

    // Re-create overlay to capture the callback
    document.body.innerHTML = "";
    container = createPlaybackOverlay(player);
    document.body.appendChild(container);

    const progressFill = container.querySelector(".playback-overlay__progress-fill") as HTMLDivElement;
    const timeLabel = container.querySelector(".playback-overlay__time-label") as HTMLDivElement;

    // Simulate tick at 50% (165000ms out of 330000ms)
    if (capturedTickCb) capturedTickCb(165000);

    expect(progressFill.style.width).toBe("50%");
    expect(timeLabel.textContent).toBe("2:45 / 5:30");
  });

  it("player state change toggles play/pause icon", () => {
    let capturedStateCb: ((state: string) => void) | undefined;
    (player.onStateChange as ReturnType<typeof vi.fn>).mockImplementation((cb) => {
      capturedStateCb = cb;
      return () => {};
    });

    // Re-create overlay to capture the callback
    document.body.innerHTML = "";
    container = createPlaybackOverlay(player);
    document.body.appendChild(container);

    const playBtn = container.querySelector("button[aria-label='Play']") as HTMLButtonElement;

    // Simulate state change to playing
    if (capturedStateCb) capturedStateCb("playing");

    expect(playBtn.textContent).toBe("⏸");
    expect(playBtn.getAttribute("aria-label")).toBe("Pause");

    // Simulate state change to paused
    if (capturedStateCb) capturedStateCb("paused");

    expect(playBtn.textContent).toBe("▶");
    expect(playBtn.getAttribute("aria-label")).toBe("Play");
  });

  it("clicking progress bar at 50% calls player.seek(durationMs * 0.5)", () => {
    const progressTrack = container.querySelector(".playback-overlay__progress-track") as HTMLDivElement;

    // Mock getBoundingClientRect to return a known width
    vi.spyOn(progressTrack, "getBoundingClientRect").mockReturnValue({
      left: 100,
      width: 400,
    } as DOMRect);

    // Simulate click at 50% (300px from left = 100 + 200)
    const clickEvent = new MouseEvent("click", {
      clientX: 300,
      bubbles: true,
    });
    progressTrack.dispatchEvent(clickEvent);

    expect(player.seek).toHaveBeenCalledWith(330000 * 0.5);
  });

  it("unsubscribe functions are called when parent element is removed", () => {
    const mockUnsubscribeTick = vi.fn();
    const mockUnsubscribeState = vi.fn();

    (player.onTick as ReturnType<typeof vi.fn>).mockReturnValue(mockUnsubscribeTick);
    (player.onStateChange as ReturnType<typeof vi.fn>).mockReturnValue(mockUnsubscribeState);

    // Re-create overlay with mocked unsubscribe functions
    document.body.innerHTML = "";
    container = createPlaybackOverlay(player);
    document.body.appendChild(container);

    container.remove();

    expect(mockUnsubscribeTick).toHaveBeenCalled();
    expect(mockUnsubscribeState).toHaveBeenCalled();
  });

  it("keyboard arrow keys seek ±5s", () => {
    const scrubArea = container.querySelector('[role="slider"]') as HTMLDivElement;

    scrubArea.focus();

    // Simulate ArrowRight key - should seek forward 5s from 0
    const rightKeyEvent = new KeyboardEvent("keydown", { key: "ArrowRight" });
    scrubArea.dispatchEvent(rightKeyEvent);

    expect(player.seek).toHaveBeenNthCalledWith(1, 5000);

    // Simulate ArrowLeft key - should seek backward 5s from 5000 to 0
    // But since player.currentTimeMs is still 0 in the mock, it seeks to -5000 (clamped by player)
    const leftKeyEvent = new KeyboardEvent("keydown", { key: "ArrowLeft" });
    scrubArea.dispatchEvent(leftKeyEvent);

    // The overlay calls player.seek(player.currentTimeMs - 5000)
    // Since mock player currentTimeMs is 0, this becomes -5000
    // The player implementation clamps it to 0
    expect(player.seek).toHaveBeenNthCalledWith(2, -5000);
  });

  it("speed buttons update active state correctly", () => {
    const speedBtns = Array.from(container.querySelectorAll(".playback-overlay__speed-btn"));
    const speed2xBtn = speedBtns.find((btn) => btn.textContent === "2×") as HTMLButtonElement;

    // Initially 1× should be active
    expect(speedBtns.find((btn) => btn.textContent === "1×")?.classList.contains("playback-overlay__speed-btn--active")).toBe(true);

    // Click 2×
    (speed2xBtn as HTMLButtonElement).click();

    // Now 2× should be active
    expect(speed2xBtn.classList.contains("playback-overlay__speed-btn--active")).toBe(true);
    expect(speedBtns.find((btn) => btn.textContent === "1×")?.classList.contains("playback-overlay__speed-btn--active")).toBe(false);
  });

  it("formats time correctly for durations over 1 hour", () => {
    const longDurationPlayer = createMockPlayer(7200000); // 2 hours
    document.body.innerHTML = "";
    container = createPlaybackOverlay(longDurationPlayer);
    document.body.appendChild(container);

    const timeLabel = container.querySelector(".playback-overlay__time-label") as HTMLDivElement;
    expect(timeLabel.textContent).toBe("0:00 / 2:00:00");
  });
});
