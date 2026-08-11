import { homedir } from "node:os";
import { join } from "node:path";
import { access, readdir } from "node:fs/promises";

/** Resolve the Chrome/Chromium executable path. */
export async function resolveChromeExecutable(): Promise<string | undefined> {
  // 1. Check env override
  const envPath = process.env.PUPPETEER_EXECUTABLE_PATH;
  if (envPath) return envPath;

  // 2. Check common Puppeteer cache locations
  const home = homedir();
  const candidates = [
    join(home, ".cache", "puppeteer", "chrome"),
  ];

  for (const dir of candidates) {
    try {
      const versions = await readdir(dir);
      for (const version of versions) {
        const linuxPath = join(dir, version, "chrome-linux64", "chrome");
        try {
          await access(linuxPath);
          return linuxPath;
        } catch {
          // continue
        }
      }
    } catch {
      // continue
    }
  }

  // 3. Fall back to undefined — Puppeteer will try its bundled chromium
  return undefined;
}
