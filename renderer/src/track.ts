/** Build track entities (polyline + waypoints) in the Cesium viewer. */
import type { TrackRenderPayload } from "./types/track.js";

export function buildTrackEntity(
  viewer: Cesium.Viewer,
  payload: TrackRenderPayload,
): void {
  for (const segment of payload.track.segments) {
    if (segment.points.length < 2) continue;

    const positions = segment.points.map((pt) =>
      Cesium.Cartesian3.fromDegrees(pt.lon, pt.lat, pt.ele ?? 0),
    );

    viewer.entities.add({
      polyline: {
        positions,
        width: 4,
        clampToGround: true,
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.2,
          color: Cesium.Color.YELLOW.withAlpha(0.9),
        }),
      },
    });
  }

  // Add waypoints as point entities
  for (const wp of payload.track.waypoints) {
    viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(
        wp.lon,
        wp.lat,
        wp.ele ?? 0,
      ),
      point: {
        pixelSize: 8,
        color: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 1,
      },
      label: {
        text: wp.name ?? "",
        font: "14px sans-serif",
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        outlineWidth: 2,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -10),
      },
    });
  }
}
