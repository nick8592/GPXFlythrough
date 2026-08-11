import puppeteer, { type Browser, type Page } from "puppeteer";
import { startStaticServer, type Server } from "./static-server.js";
import { getChromeArgs } from "./chrome-args.js";
import { resolveChromeExecutable } from "./chrome-path.js";
import type { CaptureMode } from "./probe.js";

export interface PageSetup {
  browser: Browser;
  page: Page;
  server: Server;
  port: number;
  captureMode: CaptureMode;
}

/** Set up a browser page with track data injected and renderer ready. */
export async function setupPage(
  options: {
    distDir: string;
    cacheDir: string;
    width: number;
    height: number;
    trackJson: string;
    fps: number;
    duration: number;
    heightAboveTerrain: number;
    noTerrain: boolean;
  },
): Promise<PageSetup> {
  // 1. Start static server
  const { server, port } = await startStaticServer(options.distDir);

  // 2. Launch browser
  const executablePath = await resolveChromeExecutable();
  const browserArgs = getChromeArgs(options.cacheDir);

  const browser = await puppeteer.launch({
    headless: true,
    executablePath,
    args: [
      ...browserArgs,
      `--window-size=${options.width},${options.height}`,
    ],
  });

  // 3. Create page + set viewport
  const page = await browser.newPage();
  await page.setViewport({ width: options.width, height: options.height });

  // 4. Inject track data BEFORE navigation
  await page.evaluateOnNewDocument((json) => {
    globalThis.__trackData = JSON.parse(json);
  }, options.trackJson);

  // 5. Navigate to renderer page
  const url = new URL(`http://127.0.0.1:${port}/index.html`);
  url.searchParams.set("fps", String(options.fps));
  url.searchParams.set("duration", String(options.duration));
  url.searchParams.set("height", String(options.heightAboveTerrain));
  if (options.noTerrain) {
    url.searchParams.set("no-terrain", "true");
  }

  await page.goto(url.toString(), {
    waitUntil: "domcontentloaded",
    timeout: 60_000,
  });

  // 6. Wait for renderer ready
  await page.waitForFunction(
    () => globalThis.__rendererReady === true,
    { timeout: 120_000 },
  );

  // 7. Check for renderer error
  const error = await page.evaluate(() => globalThis.__rendererError);
  if (error) {
    throw new Error(`Renderer failed: ${String(error)}`);
  }

  // 8. Wait for terrain (if applicable)
  if (!options.noTerrain) {
    await page
      .waitForFunction(
        () => {
          const viewer = globalThis.__viewer;
          return viewer?.scene?.globe?.tilesLoaded === true;
        },
        { timeout: 60_000 },
      )
      .catch(() => {
        process.stderr.write(
          "Warning: terrain load timeout, proceeding\n",
        );
      });
  }

  // 9. Default to screenshot mode; capture loop will probe beginFrame separately
  const captureMode: CaptureMode = "screenshot";

  return { browser, page, server, port, captureMode };
}
