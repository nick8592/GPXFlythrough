export interface FFmpegOptions {
  outputPath: string;
  fps: number;
  resolution: { width: number; height: number };
}

export class FFmpegError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FFmpegError";
  }
}
