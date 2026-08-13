/** Entry point for the browser-side interactive 2D map viewer. */
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { validate } from "./schema/track-render.js";
import type { TrackRenderPayload } from "./types/track.js";
import { MapCamera } from "./camera.js";
import { buildTrackLayers, buildPositionMarker } from "./track.js";
import { Player } from "./player.js";
import { createPlaybackOverlay } from "./ui/playback-overlay.js";

declare global {
  var __trackData: unknown;
  var __map: maplibregl.Map;
  var __player: Player;
  var __rendererReady: boolean;
  var __rendererError: string | undefined;
}

async function main(): Promise<void> {
  try {
    // 1. Validate payload
    const payload: TrackRenderPayload = validate(globalThis.__trackData);

    // 2. Determine map style based on theme
    const isDark = payload.render.theme === "dark";
    const mapStyle = isDark
      ? "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
      : "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

    // 3. Create map with bounds fitting
    const bounds = payload.track.bounds;
    const map = new maplibregl.Map({
      container: "mapContainer",
      style: mapStyle,
      bounds: [
        [bounds.min_lon, bounds.min_lat],
        [bounds.max_lon, bounds.max_lat],
      ],
      fitBoundsOptions: { padding: 60, maxZoom: 16 },
      interactive: true,
    });

    // 4. Wait for map to load
    await new Promise<void>((resolve) => {
      map.on("load", () => resolve());
    });

    // 5. Build track layers and position marker
    buildTrackLayers(map, payload);
    const marker = buildPositionMarker(map, payload);

    // 6. Create camera + player
    const camera = new MapCamera(map, payload);
    const durationMs = camera.getDurationMs();
    const player = new Player(camera, durationMs);

    // 7. Wire position marker to player ticks
    player.onTick((ms) => marker.setCurrentTime(ms));
    marker.setCurrentTime(0);

    // 8. Read URL params for initial speed
    const params = new URLSearchParams(window.location.search);
    const speedParam = params.get("speed");
    if (speedParam !== null) {
      const speed = Number.parseFloat(speedParam);
      if (speed > 0) {
        player.setSpeed(speed);
      }
    }

    // 9. Mount playback overlay
    const overlay = createPlaybackOverlay(player);
    document.body.appendChild(overlay);

    // 10. Expose globals
    globalThis.__map = map;
    globalThis.__player = player;
    globalThis.__rendererReady = true;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    globalThis.__rendererError = message;
    console.error("Renderer failed:", message);
  }
}

main();
