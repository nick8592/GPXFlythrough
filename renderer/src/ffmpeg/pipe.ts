import { spawn } from "node:child_process";
import type { Writable } from "node:stream";
import { resolveFfmpegPath } from "./probe.js";
import { buildFfmpegArgs } from "./args.js";
import { FFmpegError } from "../types/ffmpeg.js";

export interface FFmpegPipeResult {
  /** Write PNG frames to this stream. */
  stdin: Writable;
  /** Wait for the FFmpeg process to finish. Rejects on non-zero exit. */
  wait: () => Promise<string>; // resolves with stderr output for debugging
}

/** Spawn an FFmpeg process with stdin pipe for frame input. */
export function spawnFfmpeg(
  outputPath: string,
  fps: number,
  resolutionLabel: string,
  customFfmpegPath?: string,
): FFmpegPipeResult {
  const ffmpegBin = resolveFfmpegPath(customFfmpegPath);
  const args = buildFfmpegArgs(outputPath, fps, resolutionLabel);

  const proc = spawn(ffmpegBin, args, {
    stdio: ["pipe", "ignore", "pipe"],
  });

  const stderrChunks: Buffer[] = [];
  proc.stderr?.on("data", (chunk: Buffer) => {
    stderrChunks.push(chunk);
  });

  const wait = (): Promise<string> =>
    new Promise((resolve, reject) => {
      proc.on("close", (code) => {
        const stderr = Buffer.concat(stderrChunks).toString("utf-8");
        if (code === 0) {
          resolve(stderr);
        } else {
          reject(new FFmpegError(`ffmpeg exited with code ${code}:\n${stderr}`));
        }
      });
      proc.on("error", (err) => {
        reject(new FFmpegError(`ffmpeg process error: ${err.message}`));
      });
    });

  if (!proc.stdin) {
    throw new FFmpegError("ffmpeg stdin stream is unavailable");
  }

  return { stdin: proc.stdin, wait };
}

/** Write a buffer to a writable stream with backpressure handling. */
export async function writeWithBackpressure(
  stream: Writable,
  buffer: Buffer,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const canWrite = stream.write(buffer);
    if (canWrite) {
      resolve();
    } else {
      stream.once("drain", resolve);
      stream.once("error", reject);
    }
  });
}
