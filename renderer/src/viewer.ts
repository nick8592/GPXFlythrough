/** Create a CesiumJS Viewer configured for interactive playback. */
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
    // Enable CesiumJS built-in timeline as fallback
    animation: false,
    timeline: false,
    // Disable chrome that we don't need
    baseLayerPicker: false,
    fullscreenButton: false,
    vrButton: false,
    geocoder: false,
    homeButton: false,
    infoBox: false,
    sceneModePicker: false,
    selectionIndicator: false,
    navigationHelpButton: false,
    // Continuous rendering for smooth playback
    requestRenderMode: false,
    maximumRenderTimeChange: Infinity,
  });

  // Hide credit container
  (
    viewer.cesiumWidget.creditContainer as HTMLElement
  ).style.display = "none";

  return viewer;
}
