/** Resolution label to pixel dimensions. */
const RESOLUTION_MAP: Record<string, [number, number]> = {
  "720p": [1280, 720],
  "1080p": [1920, 1080],
  "4k": [3840, 2160],
};

/** Build the FFmpeg argument array for H.264 encoding from PNG image pipe. */
export function buildFfmpegArgs(
  outputPath: string,
  fps: number,
  resolutionLabel: string,
): string[] {
  const dims = RESOLUTION_MAP[resolutionLabel];
  if (dims === undefined) {
    throw new Error(`Unknown resolution label: ${resolutionLabel}`);
  }
  const [width, height] = dims;

  return [
    "-y",                          // overwrite output
    "-f", "image2pipe",            // input format: PNG pipe
    "-vcodec", "png",              // input codec
    "-r", String(fps),             // input framerate
    "-thread_queue_size", "1024",  // input thread queue
    "-i", "pipe:0",                // read from stdin
    "-c:v", "libx264",             // video codec
    "-pix_fmt", "yuv420p",         // pixel format (compatible with most players)
    "-crf", "18",                  // quality (lower = better, 18 is visually lossless)
    "-preset", "veryfast",         // encoding speed preset
    "-movflags", "+faststart",     // move moov atom for streaming
    "-vf", `scale=${width}:${height}`, // force output resolution
    outputPath,
  ];
}
