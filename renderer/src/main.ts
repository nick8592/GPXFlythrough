/** Entry point for the browser-side interactive 3D flythrough viewer. */
import { validate } from "./schema/track-render.js";
import type { TrackRenderPayload } from "./types/track.js";
import { createViewer } from "./viewer.js";
import { loadTerrain } from "./terrain.js";
import { buildTrackEntity, buildPositionMarker } from "./track.js";
import { FollowCamera } from "./camera.js";
import { Player } from "./player.js";
import { applyTheme } from "./theme.js";
import { createPlaybackOverlay } from "./ui/playback-overlay.js";

declare global {
  var __trackData: unknown;
  var __viewer: Cesium.Viewer;
  var __player: Player;
  var __rendererReady: boolean;
  var __rendererError: string | undefined;
}

async function main(): Promise<void> {
  try {
    // 1. Validate payload
    const payload: TrackRenderPayload = validate(globalThis.__trackData);

    // 2. Create viewer
    const noTerrain = payload.render.no_terrain;
    const renderExtra = payload.render as unknown as Record<string, unknown>;
    const ionToken = renderExtra.ion_token as string | undefined;
    const viewer = createViewer("cesiumContainer");

    // 3. Load terrain
    await loadTerrain(viewer, noTerrain, ionToken);

    // 4. Apply theme
    applyTheme(viewer, payload.render.theme);

    // 5. Build track entities
    buildTrackEntity(viewer, payload);

    // 6. Create camera + player
    const camera = new FollowCamera(viewer, payload);
    const durationMs = camera.getDurationMs();
    const player = new Player(camera, durationMs);

    // 7. Build position marker and wire to player ticks
    const marker = buildPositionMarker(viewer, payload);
    player.onTick((ms) => marker.setCurrentTime(ms));
    marker.setCurrentTime(0);

    // 8. Read URL params for initial speed override
    const params = new URLSearchParams(window.location.search);
    const speedParam = params.get("speed");
    if (speedParam !== null) {
      const speed = Number.parseFloat(speedParam);
      if (speed > 0) {
        player.setSpeed(speed);
      }
    }

    // 9. Mount playback UI overlay
    const overlay = createPlaybackOverlay(player);
    document.body.appendChild(overlay);

    // 10. Set global references for debugging
    globalThis.__viewer = viewer;
    globalThis.__player = player;
    globalThis.__rendererReady = true;
  } catch (err) {
    const message =
      err instanceof Error ? err.message : String(err);
    globalThis.__rendererError = message;
    console.error("Renderer failed:", message);
  }
}

main();
