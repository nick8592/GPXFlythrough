import { describe, it, expect } from "vitest";
import { parseFfmpegVersion, isVersionAtLeast } from "../ffmpeg/probe.js";

describe("parseFfmpegVersion", () => {
  it("parses standard ffmpeg version output", () => {
    const result = parseFfmpegVersion("ffmpeg version 8.0.1-3ubuntu2 Copyright ...");
    expect(result).toEqual({ major: 8, minor: 0 });
  });

  it("parses version 4.1", () => {
    const result = parseFfmpegVersion("ffmpeg version 4.1.0");
    expect(result).toEqual({ major: 4, minor: 1 });
  });

  it("throws on non-matching input", () => {
    expect(() => parseFfmpegVersion("not ffmpeg")).toThrow();
  });
});

describe("isVersionAtLeast", () => {
  it("8.0 is at least 4.1", () => {
    expect(isVersionAtLeast({ major: 8, minor: 0 }, { major: 4, minor: 1 })).toBe(true);
  });

  it("4.0 is NOT at least 4.1", () => {
    expect(isVersionAtLeast({ major: 4, minor: 0 }, { major: 4, minor: 1 })).toBe(false);
  });

  it("4.1 is at least 4.1", () => {
    expect(isVersionAtLeast({ major: 4, minor: 1 }, { major: 4, minor: 1 })).toBe(true);
  });

  it("5.0 is at least 4.1", () => {
    expect(isVersionAtLeast({ major: 5, minor: 0 }, { major: 4, minor: 1 })).toBe(true);
  });
});
