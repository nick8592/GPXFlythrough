import type { Player, PlayerState } from "../player.js";
import "./playback-overlay.css";

export function createPlaybackOverlay(player: Player): HTMLElement {
  const container = document.createElement("div");
  container.className = "playback-overlay";

  // Play/Pause button
  const playBtn = document.createElement("button");
  playBtn.className = "playback-overlay__play-btn";
  playBtn.setAttribute("aria-label", "Play");
  playBtn.textContent = "▶";

  // Progress bar container
  const progressContainer = document.createElement("div");
  progressContainer.className = "playback-overlay__progress-container";

  // Progress track
  const progressTrack = document.createElement("div");
  progressTrack.className = "playback-overlay__progress-track";

  // Progress fill
  const progressFill = document.createElement("div");
  progressFill.className = "playback-overlay__progress-fill";
  progressFill.style.width = "0%";

  // Clickable scrub area
  const scrubArea = document.createElement("div");
  scrubArea.className = "playback-overlay__scrub-area";
  scrubArea.setAttribute("role", "slider");
  scrubArea.setAttribute("aria-label", "Playback progress");
  scrubArea.setAttribute("aria-valuemin", "0");
  scrubArea.setAttribute("aria-valuemax", "100");
  scrubArea.setAttribute("aria-valuenow", "0");
  scrubArea.setAttribute("tabindex", "0");

  progressTrack.appendChild(progressFill);
  progressContainer.appendChild(progressTrack);
  progressContainer.appendChild(scrubArea);

  // Time labels
  const timeLabel = document.createElement("div");
  timeLabel.className = "playback-overlay__time-label";
  timeLabel.textContent = "0:00 / 0:00";

  // Speed selector container
  const speedContainer = document.createElement("div");
  speedContainer.className = "playback-overlay__speed-container";

  // Speed buttons
  const speeds = [0.5, 1, 2, 4];
  const speedBtns: HTMLButtonElement[] = [];

  for (const speed of speeds) {
    const btn = document.createElement("button");
    btn.className = "playback-overlay__speed-btn";
    btn.textContent = `${speed}×`;
    btn.setAttribute("aria-label", `Speed ${speed}x`);
    if (speed === 1) {
      btn.classList.add("playback-overlay__speed-btn--active");
    }
    speedBtns.push(btn);
    speedContainer.appendChild(btn);
  }

  // Assemble the overlay
  container.appendChild(playBtn);
  container.appendChild(progressContainer);
  container.appendChild(timeLabel);
  container.appendChild(speedContainer);

  // Helper: format time as M:SS or H:MM:SS
  function formatTime(ms: number): string {
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  }

  // Helper: update progress bar and time label
  function updateProgress(currentMs?: number) {
    const current = currentMs ?? player.currentTimeMs;
    const duration = player.durationMs;
    const fraction = duration > 0 ? current / duration : 0;
    const percentage = fraction * 100;

    progressFill.style.width = `${percentage}%`;
    scrubArea.setAttribute("aria-valuenow", Math.round(percentage).toString());

    timeLabel.textContent = `${formatTime(current)} / ${formatTime(duration)}`;
  }

  // Helper: update play button icon and aria-label
  function updatePlayButton(state: PlayerState) {
    if (state === "playing") {
      playBtn.textContent = "⏸";
      playBtn.setAttribute("aria-label", "Pause");
    } else {
      playBtn.textContent = "▶";
      playBtn.setAttribute("aria-label", "Play");
    }
  }

  // Play/Pause button click handler
  playBtn.addEventListener("click", () => {
    player.togglePlay();
  });

  // Progress bar click handler - seek to clicked position
  progressContainer.addEventListener("click", (e) => {
    const rect = progressTrack.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const fraction = Math.max(0, Math.min(1, x / rect.width));
    player.seek(player.durationMs * fraction);
  });

  // Keyboard navigation for progress bar
  scrubArea.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
      e.preventDefault();
      player.seek(player.currentTimeMs - 5000);
    } else if (e.key === "ArrowRight" || e.key === "ArrowUp") {
      e.preventDefault();
      player.seek(player.currentTimeMs + 5000);
    } else if (e.key === "Home") {
      e.preventDefault();
      player.seek(0);
    } else if (e.key === "End") {
      e.preventDefault();
      player.seek(player.durationMs);
    }
  });

  // Speed button click handlers
  for (const btn of speedBtns) {
    btn.addEventListener("click", () => {
      const speedText = btn.textContent;
      const speed = parseFloat(speedText?.replace("×", "") || "1");
      player.setSpeed(speed);

      // Update active state
      for (const b of speedBtns) {
        b.classList.remove("playback-overlay__speed-btn--active");
      }
      btn.classList.add("playback-overlay__speed-btn--active");
    });
  }

  // Subscribe to player events
  const unsubscribeTick = player.onTick((ms) => {
    updateProgress(ms);
  });

  const unsubscribeState = player.onStateChange((state) => {
    updatePlayButton(state);
  });

  // Initial state sync
  updateProgress();
  updatePlayButton(player.state);

  // Cleanup when element is removed from DOM
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === "childList") {
        const removedNodes = Array.from(mutation.removedNodes);
        if (removedNodes.includes(container) || !document.contains(container)) {
          observer.disconnect();
          unsubscribeTick();
          unsubscribeState();
        }
      }
    }
  });

  // Start observing after a microtask to ensure element is in DOM
  queueMicrotask(() => {
    if (document.contains(container)) {
      observer.observe(document.body, { childList: true, subtree: true });
    }
  });

  // Also handle direct removal via disconnectedCallback pattern
  const originalRemove = container.remove.bind(container);
  container.remove = function () {
    observer.disconnect();
    unsubscribeTick();
    unsubscribeState();
    originalRemove();
  };

  return container;
}
