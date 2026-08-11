/** Entry point for the browser-side renderer. */
import { validate } from "./schema/track-render.js";
import type { TrackRenderPayload } from "./types/track.js";
import { createViewer } from "./viewer.js";
import { loadTerrain } from "./terrain.js";
import { buildTrackEntity } from "./track.js";
import { FollowCamera } from "./camera.js";
import { Player } from "./player.js";
import { applyTheme } from "./theme.js";

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

    // 4. Apply dark theme
    applyTheme(viewer, payload.render.theme);

    // 5. Build track entities
    buildTrackEntity(viewer, payload);

    // 6. Create camera + player
    const camera = new FollowCamera(viewer, payload);
    const params = new URLSearchParams(window.location.search);
    const overrideDuration = params.get("duration");
    const overrideDurationS = overrideDuration ? Number.parseFloat(overrideDuration) : undefined;
    const player = new Player(payload, camera, overrideDurationS);

    // 7. Set global references for Puppeteer
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
