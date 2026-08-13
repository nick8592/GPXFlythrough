/** Build track entities (polyline + waypoints) in the Cesium viewer. */
import type { TrackRenderPayload } from "./types/track.js";
import { getPointAtTime } from "./camera.js";

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
        width: 6,
        clampToGround: true,
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.15,
          color: Cesium.Color.fromCssColorString("#FF6B35"),
        }),
      },
    });
  }

  for (const wp of payload.track.waypoints) {
    viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(
        wp.lon,
        wp.lat,
        wp.ele ?? 0,
      ),
      point: {
        pixelSize: 12,
        color: Cesium.Color.fromCssColorString("#FF6B35"),
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: wp.name ?? "",
        font: "14px sans-serif",
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 3,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -14),
      },
    });
  }
}

export interface PositionMarker {
  setCurrentTime(ms: number): void;
}

export function buildPositionMarker(
  viewer: Cesium.Viewer,
  payload: TrackRenderPayload,
): PositionMarker {
  const segments = payload.track.segments;
  const firstPoint = segments[0]?.points[0];
  let currentTimeMs = 0;

  viewer.entities.add({
    position: new Cesium.CallbackProperty(() => {
      const point = getPointAtTime(segments, currentTimeMs);
      if (point === null) {
        return Cesium.Cartesian3.fromDegrees(
          firstPoint?.lon ?? 0,
          firstPoint?.lat ?? 0,
        );
      }
      return Cesium.Cartesian3.fromDegrees(point.lon, point.lat);
    }, false),
    point: {
      pixelSize: 20,
      color: Cesium.Color.fromCssColorString("#FF6B35"),
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 3,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  });

  return {
    setCurrentTime(ms: number): void {
      currentTimeMs = ms;
    },
  };
}
