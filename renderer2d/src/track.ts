/** Build track visualization on the MapLibre map. */
import type { Map as MapLibreMap, GeoJSONSource, LayerSpecification, GeoJSONSourceSpecification } from "maplibre-gl";
import type { TrackRenderPayload, Point } from "./types/track.js";
import { getPointAtTime } from "./camera.js";

/**
 * Add track-segment line sources/layers (with `line-gradient` for the
 * drawing animation) and waypoint markers to the map.
 *
 * Source IDs: `segment-{i}`     Layer IDs: `segment-{i}-line`
 * Source IDs: `waypoint-{i}`    Layer IDs: `waypoint-{i}-circle`, `waypoint-{i}-label`
 *
 * The initial `line-gradient` renders the entire segment as undrawn.
 */
export function buildTrackLayers(
  map: MapLibreMap,
  payload: TrackRenderPayload,
): void {
  // Track segments — one source+layer per segment (line-gradient requires LineString).
  for (let i = 0; i < payload.track.segments.length; i++) {
    const segment = payload.track.segments[i];
    if (segment === undefined) continue;
    if (segment.points.length < 2) continue;

    const coordinates: [number, number][] = segment.points.map((pt: Point) => [
      pt.lon,
      pt.lat,
    ]);

    const sourceId = `segment-${i}`;
    const layerId = `${sourceId}-line`;

    const sourceSpec: GeoJSONSourceSpecification = {
      type: "geojson",
      lineMetrics: true,
      data: {
        type: "Feature",
        geometry: { type: "LineString", coordinates },
        properties: {},
      },
    };
    map.addSource(sourceId, sourceSpec);

    const layer: LayerSpecification = {
      id: layerId,
      type: "line",
      source: sourceId,
      layout: {
        "line-cap": "round",
        "line-join": "round",
      },
      paint: {
        "line-width": 4,
        "line-gradient": [
          "interpolate",
          ["linear"],
          ["line-progress"],
          0,
          "rgba(255,255,255,0.15)",
          1,
          "rgba(255,255,255,0.15)",
        ],
      },
    };
    map.addLayer(layer);
  }

  // Waypoints — circle marker + label per waypoint.
  for (let i = 0; i < payload.track.waypoints.length; i++) {
    const wp = payload.track.waypoints[i];
    if (wp === undefined) continue;

    const sourceId = `waypoint-${i}`;
    const circleLayerId = `${sourceId}-circle`;
    const labelLayerId = `${sourceId}-label`;

    const sourceSpec: GeoJSONSourceSpecification = {
      type: "geojson",
      data: {
        type: "Feature",
        geometry: { type: "Point", coordinates: [wp.lon, wp.lat] },
        properties: { name: wp.name ?? "" },
      },
    };
    map.addSource(sourceId, sourceSpec);

    const circleLayer: LayerSpecification = {
      id: circleLayerId,
      type: "circle",
      source: sourceId,
      paint: {
        "circle-radius": 6,
        "circle-color": "#FFFFFF",
        "circle-stroke-color": "#000000",
        "circle-stroke-width": 1.5,
      },
    };
    map.addLayer(circleLayer);

    if (wp.name !== null && wp.name !== "") {
      const labelLayer: LayerSpecification = {
        id: labelLayerId,
        type: "symbol",
        source: sourceId,
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
          "text-size": 12,
          "text-offset": [0, 1.2],
          "text-anchor": "top",
          "text-allow-overlap": false,
        },
        paint: {
          "text-color": "#FFFFFF",
          "text-halo-color": "#000000",
          "text-halo-width": 1.5,
        },
      };
      map.addLayer(labelLayer);
    }
  }
}

export interface PositionMarker {
  setCurrentTime(ms: number): void;
}

/**
 * Add a position-marker layer (cyan dot) at the current playback position.
 * Returns an object whose `setCurrentTime(ms)` moves the marker.
 */
export function buildPositionMarker(
  map: MapLibreMap,
  payload: TrackRenderPayload,
): PositionMarker {
  const sourceId = "position-marker";
  const layerId = "position-marker-circle";

  const segments = payload.track.segments;
  const firstPoint = segments[0]?.points[0];
  const initialLonLat: [number, number] = [
    firstPoint?.lon ?? 0,
    firstPoint?.lat ?? 0,
  ];

  const sourceSpec: GeoJSONSourceSpecification = {
    type: "geojson",
    data: {
      type: "Feature",
      geometry: { type: "Point", coordinates: initialLonLat },
      properties: {},
    },
  };
  map.addSource(sourceId, sourceSpec);

  const layer: LayerSpecification = {
    id: layerId,
    source: sourceId,
    type: "circle",
    paint: {
      "circle-radius": 8,
      "circle-color": "#00FFFF",
      "circle-stroke-color": "#FFFFFF",
      "circle-stroke-width": 3,
    },
  };
  map.addLayer(layer);

  return {
    setCurrentTime(ms: number): void {
      const point = getPointAtTime(segments, ms);
      const coords: [number, number] =
        point !== null ? [point.lon, point.lat] : initialLonLat;
      const source = map.getSource(sourceId) as GeoJSONSource | undefined;
      if (source !== undefined) {
        source.setData({
          type: "Feature",
          geometry: { type: "Point", coordinates: coords },
          properties: {},
        });
      }
    },
  };
}
