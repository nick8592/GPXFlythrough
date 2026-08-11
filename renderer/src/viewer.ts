/** Create a CesiumJS Viewer configured for headless rendering. */
export function createViewer(
  containerId: string,
): Cesium.Viewer {
  const container = document.getElementById(containerId);
  if (container === null) {
    throw new Error(`Container element #${containerId} not found`);
  }

  const viewer = new Cesium.Viewer(container, {
    // Disable terrain by default; loadTerrain() will set it up
    terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    // Disable all UI chrome for clean rendering
    animation: false,
    timeline: false,
    baseLayerPicker: false,
    fullscreenButton: false,
    vrButton: false,
    geocoder: false,
    homeButton: false,
    infoBox: false,
    sceneModePicker: false,
    selectionIndicator: false,
    navigationHelpButton: false,
    // Continuous rendering for frame capture
    requestRenderMode: false,
    maximumRenderTimeChange: Infinity,
  });

  // Hide credit container
  (
    viewer.cesiumWidget.creditContainer as HTMLElement
  ).style.display = "none";

  return viewer;
}
