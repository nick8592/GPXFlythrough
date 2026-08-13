/** Terrain loading — Cesium Ion or ellipsoid fallback. */
export async function loadTerrain(
  viewer: Cesium.Viewer,
  noTerrain: boolean,
  ionToken?: string,
): Promise<void> {
  if (!noTerrain && ionToken !== undefined && ionToken !== "") {
    try {
      Cesium.Ion.defaultAccessToken = ionToken;
      const terrain = await Cesium.createWorldTerrainAsync();
      viewer.terrainProvider = terrain;
    } catch (err) {
      console.warn(
        "Failed to load Cesium Ion terrain, falling back to ellipsoid:",
        err,
      );
    }
  }

  // Wait for terrain tiles to load (or just proceed for ellipsoid)
  if (!noTerrain) {
    await waitForTerrainReady(viewer, 30_000);
  }
}

function waitForTerrainReady(
  viewer: Cesium.Viewer,
  timeoutMs: number,
): Promise<void> {
  return new Promise((resolve) => {
    const start = Date.now();
    const check = (): void => {
      if (viewer.scene.globe.tilesLoaded) {
        resolve();
        return;
      }
      if (Date.now() - start > timeoutMs) {
        console.warn(
          "Terrain load timeout, proceeding with partial terrain",
        );
        resolve();
        return;
      }
      setTimeout(check, 500);
    };
    check();
  });
}
