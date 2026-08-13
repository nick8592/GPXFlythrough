/** Schema version — must match Python's "1.0.0". */
export type SchemaVersion = "1.0.0";

export interface Bounds {
  min_lat: number;
  max_lat: number;
  min_lon: number;
  max_lon: number;
  min_ele: number;
  max_ele: number;
}

export interface Point {
  lat: number;
  lon: number;
  ele: number | null;
  time: string | null;
  cumulative_m: number;
  speed: number | null;
  hr: number | null;
  cad: number | null;
  temp: number | null;
}

export interface Segment {
  index: number;
  start_time_iso: string | null;
  duration_s: number;
  length_m: number;
  points: Point[];
}

export interface Waypoint {
  lat: number;
  lon: number;
  ele: number | null;
  name: string | null;
  time: string | null;
}

export interface Track {
  name: string;
  activity_type: string | null;
  bounds: Bounds;
  segments: Segment[];
  waypoints: Waypoint[];
}

export interface Resolution {
  label: string;
  width: number;
  height: number;
}

export interface Camera {
  mode: string;
  height_above_terrain_m: number;
  lookahead_m: number;
  pitch_deg: number;
}

export interface Render {
  fps: number;
  resolution: Resolution;
  camera: Camera;
  theme: string;
  overlays: string[];
  no_terrain: boolean;
}

export interface TrackRenderPayload {
  schema_version: SchemaVersion;
  track: Track;
  render: Render;
}
