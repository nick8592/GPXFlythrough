import type { CDPSession } from "puppeteer";
import { setupPage, type PageSetup } from "./setup.js";

export interface CaptureOptions {
  distDir: string;
  cacheDir: string;
  width: number;
  height: number;
  trackJson: string;
  fps: number;
  duration: number;
  heightAboveTerrain: number;
  noTerrain: boolean;
}

const PAGE_RECYCLE_INTERVAL = 500;

/** Async generator that yields PNG frame buffers one at a time. */
export async function* captureFrames(
  options: CaptureOptions,
): AsyncGenerator<Buffer, void, void> {
  let setup: PageSetup | null = null;
  let frameIndex = 0;

  try {
    setup = await setupPage(options);
    const totalDurationMs = options.duration * 1000;
    const totalFrames = Math.floor(totalDurationMs / (1000 / options.fps));
    const frameIntervalMs = 1000 / options.fps;

    process.stderr.write(
      `Capturing ${totalFrames} frames at ${options.fps}fps (${options.duration.toFixed(1)}s)\n`,
    );

    let cdpSession: CDPSession | null = null;
    if (setup.captureMode === "beginFrame") {
      cdpSession = await setup.page.createCDPSession();
    }

    while (frameIndex < totalFrames) {
      if (frameIndex > 0 && frameIndex % PAGE_RECYCLE_INTERVAL === 0) {
        process.stderr.write(`Recycling page at frame ${frameIndex}...\n`);
        await setup.page.close();
        setup = await setupPage(options);
        cdpSession =
          setup.captureMode === "beginFrame"
            ? await setup.page.createCDPSession()
            : null;
      }

      const timeMs = frameIndex * frameIntervalMs;

      await setup.page.evaluate(
        (t) => globalThis.__player.seek(t),
        timeMs,
      );

      await setup.page.evaluate(
        () =>
          new Promise<void>((resolve) => {
            requestAnimationFrame(() => resolve());
          }),
      );

      let pngBuffer: Buffer;

      if (setup.captureMode === "beginFrame" && cdpSession) {
        const result = await cdpSession.send(
          "HeadlessExperimental.beginFrame",
          {
            frameTimeTicks: performance.now(),
            screenshot: { format: "png" },
          },
        );
        const data = result.screenshotData;
        if (data === undefined) {
          throw new Error("beginFrame returned no screenshot data");
        }
        pngBuffer = Buffer.from(data, "base64");
      } else {
        const screenshot = await setup.page.screenshot({ type: "png" });
        pngBuffer = Buffer.isBuffer(screenshot)
          ? screenshot
          : Buffer.from(screenshot);
      }

      yield pngBuffer;

      frameIndex++;
    }
  } finally {
    if (setup) {
      await setup.browser.close().catch(() => {});
      setup.server.close();
    }
  }
}
