import { describe, it, expect } from "vitest";
import { getChromeArgs } from "../capture/chrome-args.js";

describe("getChromeArgs", () => {
  it("includes --disable-gpu flag", () => {
    const args = getChromeArgs("/tmp/cache");
    expect(args).toContain("--disable-gpu");
  });

  it("includes --enable-unsafe-swiftshader flag", () => {
    const args = getChromeArgs("/tmp/cache");
    expect(args).toContain("--enable-unsafe-swiftshader");
  });

  it("includes --no-sandbox flag", () => {
    const args = getChromeArgs("/tmp/cache");
    expect(args).toContain("--no-sandbox");
  });

  it("includes custom cache dir", () => {
    const args = getChromeArgs("/custom/cache/path");
    expect(args).toContain("--disk-cache-dir=/custom/cache/path");
  });

  it("includes --disable-dev-shm-usage flag", () => {
    const args = getChromeArgs("/tmp/cache");
    expect(args).toContain("--disable-dev-shm-usage");
  });

  it("omits --disk-cache-dir when cacheDir is empty", () => {
    const args = getChromeArgs("");
    expect(args.some((a) => a.startsWith("--disk-cache-dir"))).toBe(false);
  });
});
