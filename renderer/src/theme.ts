/** Apply visual theme to the Cesium viewer. */
export function applyTheme(
  viewer: Cesium.Viewer,
  theme: string,
): void {
  const scene = viewer.scene;

  switch (theme) {
    case "dark":
      scene.skyBox.show = false;
      scene.skyAtmosphere.show = false;
      scene.backgroundColor = Cesium.Color.BLACK;
      scene.globe.baseColor =
        Cesium.Color.fromCssColorString("#1a1a1a");
      scene.globe.enableLighting = true;
      break;
    case "light":
      scene.skyBox.show = true;
      scene.skyAtmosphere.show = true;
      scene.backgroundColor = Cesium.Color.WHITE;
      scene.globe.baseColor =
        Cesium.Color.fromCssColorString("#e0e0e0");
      break;
    case "transparent":
      scene.skyBox.show = false;
      scene.skyAtmosphere.show = false;
      scene.backgroundColor = new Cesium.Color(0, 0, 0, 0);
      scene.globe.baseColor =
        Cesium.Color.fromCssColorString("#2a2a2a");
      break;
    default:
      // Default to dark
      scene.skyBox.show = false;
      scene.skyAtmosphere.show = false;
      scene.backgroundColor = Cesium.Color.BLACK;
      scene.globe.baseColor =
        Cesium.Color.fromCssColorString("#1a1a1a");
  }
}
