import { execFileSync } from "node:child_process";
import { FFmpegError } from "../types/ffmpeg.js";

interface Version {
  major: number;
  minor: number;
}

const MINIMUM_VERSION: Version = { major: 4, minor: 1 };

/** Parse version string from `ffmpeg -version` output. */
export function parseFfmpegVersion(output: string): Version {
  const match = output.match(/ffmpeg version (\d+)\.(\d+)/);
  if (!match || match[1] === undefined || match[2] === undefined) {
    throw new FFmpegError(`Cannot parse ffmpeg version from: ${output.slice(0, 100)}`);
  }
  return { major: Number.parseInt(match[1], 10), minor: Number.parseInt(match[2], 10) };
}

/** Check if a parsed version meets the minimum requirement. */
export function isVersionAtLeast(version: Version, minimum: Version): boolean {
  if (version.major > minimum.major) return true;
  if (version.major === minimum.major && version.minor >= minimum.minor) return true;
  return false;
}

/** Resolve FFmpeg binary path. Checks customPath first, then system PATH. */
export function resolveFfmpegPath(customPath?: string): string {
  const binary = customPath ?? "ffmpeg";
  try {
    const output = execFileSync(binary, ["-version"], {
      encoding: "utf-8",
      timeout: 5_000,
    });
    const version = parseFfmpegVersion(output);
    if (!isVersionAtLeast(version, MINIMUM_VERSION)) {
      throw new FFmpegError(
        `ffmpeg version ${version.major}.${version.minor} is below minimum ${MINIMUM_VERSION.major}.${MINIMUM_VERSION.minor}. ` +
        `Install a newer version: https://ffmpeg.org/download.html`,
      );
    }
    return binary;
  } catch (err) {
    if (err instanceof FFmpegError) throw err;
    throw new FFmpegError(
      `ffmpeg not found at "${binary}". Install FFmpeg >= 4.1: https://ffmpeg.org/download.html`,
    );
  }
}

/** Validate that the FFmpeg binary meets version requirements. Throws on failure. */
export function validateFfmpegVersion(customPath?: string): string {
  return resolveFfmpegPath(customPath);
}
