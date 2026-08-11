import type { Page } from "puppeteer";

export type CaptureMode = "beginFrame" | "screenshot";

/** Probe which headless capture mode is available. Prefer CDP beginFrame. */
export async function probeCaptureMode(
  page: Page,
): Promise<{ mode: CaptureMode; session: import("puppeteer").CDPSession | null }> {
  try {
    const client = await page.createCDPSession();
    await client.send("HeadlessExperimental.enable");
    // Keep the session for reuse during capture
    return { mode: "beginFrame", session: client };
  } catch {
    process.stderr.write(
      "Warning: HeadlessExperimental.beginFrame not available, falling back to Page.captureScreenshot\n",
    );
    return { mode: "screenshot", session: null };
  }
}
