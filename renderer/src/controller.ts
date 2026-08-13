export interface CameraController {
  seek(ms: number): void;
  getDurationMs(): number;
}
