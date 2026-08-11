import { describe, it, expect } from "vitest";
import { buildFfmpegArgs } from "../ffmpeg/args.js";

describe("buildFfmpegArgs", () => {
  it("produces correct args for 1080p/30fps", () => {
    const args = buildFfmpegArgs("/tmp/out.mp4", 30, "1080p");
    expect(args).toEqual([
      "-y",
      "-f", "image2pipe",
      "-vcodec", "png",
      "-r", "30",
      "-thread_queue_size", "1024",
      "-i", "pipe:0",
      "-c:v", "libx264",
      "-pix_fmt", "yuv420p",
      "-crf", "18",
      "-preset", "veryfast",
      "-movflags", "+faststart",
      "-vf", "scale=1920:1080",
      "/tmp/out.mp4",
    ]);
  });

  it("produces correct args for 720p/24fps", () => {
    const args = buildFfmpegArgs("/tmp/smoke.mp4", 24, "720p");
    expect(args).toContain("-r");
    expect(args).toContain("24");
    expect(args).toContain("scale=1280:720");
  });

  it("produces correct args for 4k/60fps", () => {
    const args = buildFfmpegArgs("/tmp/4k.mp4", 60, "4k");
    expect(args).toContain("60");
    expect(args).toContain("scale=3840:2160");
  });

  it("throws for unknown resolution", () => {
    expect(() => buildFfmpegArgs("/tmp/out.mp4", 30, "8k")).toThrow("Unknown resolution");
  });
});
