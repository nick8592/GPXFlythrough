#!/usr/bin/env node
/** CLI entry point for the GPXFlythrough renderer. */

import { readFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnFfmpeg, writeWithBackpressure } from "../ffmpeg/pipe.js";
import { captureFrames } from "../capture/capture.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

const HELP = `
GPXFlythrough Renderer — headless frame capture → FFmpeg → MP4

Usage:
  render --input <track.json> [options]

Required:
  --input <path>            Track JSON file path

Options:
  --output <path>           Output MP4 file (default: output.mp4)
  --resolution <label>      720p | 1080p | 4k  (default: 1080p)
  --fps <number>            Frame rate (default: 30)
  --height <meters>         Camera height above terrain (default: 50)
  --duration <seconds>      Render duration in seconds (default: 30)
  --cache-dir <path>        Chrome disk cache directory
  --no-terrain              Disable terrain rendering
  --ffmpeg-path <path>      Custom FFmpeg binary path
  --token <string>          Cesium Ion access token
  --help                    Show this help message
`.trim();

interface CliArgs {
  input: string;
  output: string;
  resolution: string;
  fps: number;
  height: number;
  duration: number;
  cacheDir: string;
  noTerrain: boolean;
  ffmpegPath: string | undefined;
  token: string | undefined;
}

function parseArgs(argv: string[]): CliArgs | null {
  const args: Record<string, string> = {};
  let i = 0;
  while (i < argv.length) {
    const current = argv[i];
    if (current === "--help") {
      return null;
    }
    if (current?.startsWith("--")) {
      const key = current.slice(2);
      const value = argv[i + 1];
      if (value && !value.startsWith("--")) {
        args[key] = value;
        i += 2;
      } else {
        args[key] = "true";
        i += 1;
      }
    } else {
      i += 1;
    }
  }

  if (!args.input) {
    console.error("Missing required flag: --input <file>");
    process.exit(1);
  }

  return {
    input: args.input,
    output: args.output ?? "output.mp4",
    resolution: args.resolution ?? "1080p",
    fps: Number(args.fps) || 30,
    height: Number(args.height) || 50,
    duration: Number(args.duration) || 30,
    cacheDir: args["cache-dir"] ?? "/tmp/gpx-renderer-chrome-cache",
    noTerrain: args["no-terrain"] === "true",
    ffmpegPath: args["ffmpeg-path"],
    token: args.token,
  };
}

const RESOLUTION_MAP: Record<string, [number, number]> = {
  "720p": [1280, 720],
  "1080p": [1920, 1080],
  "4k": [3840, 2160],
};

async function main(): Promise<void> {
  const cliArgs = parseArgs(process.argv.slice(2));
  if (cliArgs === null) {
    console.log(HELP);
    return;
  }

  // Read track JSON
  const inputPath = cliArgs.input.startsWith("file://")
    ? fileURLToPath(cliArgs.input)
    : cliArgs.input;
  const trackJson = await readFile(inputPath, "utf-8");

  // Resolution dimensions
  const dims = RESOLUTION_MAP[cliArgs.resolution] ?? [1920, 1080];

  // Dist directory (where the built renderer HTML lives)
  const distDir = resolve(__dirname, "..");

  // Spawn FFmpeg
  const ffmpeg = spawnFfmpeg(
    cliArgs.output,
    cliArgs.fps,
    cliArgs.resolution,
    cliArgs.ffmpegPath,
  );

  // Capture frames and pipe to FFmpeg
  let frameCount = 0;
  try {
    for await (const pngBuffer of captureFrames({
      distDir,
      cacheDir: cliArgs.cacheDir,
      width: dims[0],
      height: dims[1],
      trackJson,
      fps: cliArgs.fps,
      duration: cliArgs.duration,
      heightAboveTerrain: cliArgs.height,
      noTerrain: cliArgs.noTerrain,
    })) {
      await writeWithBackpressure(ffmpeg.stdin, pngBuffer);
      frameCount++;
    }

    // Signal end of input
    ffmpeg.stdin.end();

    // Wait for FFmpeg to finish
    const stderr = await ffmpeg.wait();
    if (stderr) {
      process.stderr.write(stderr);
    }

    process.stderr.write(
      `\nDone: ${frameCount} frames → ${cliArgs.output}\n`,
    );
  } catch (err) {
    ffmpeg.stdin.destroy();
    throw err;
  }
}

main().catch((err) => {
  console.error(
    "Render failed:",
    err instanceof Error ? err.message : err,
  );
  process.exit(1);
});
