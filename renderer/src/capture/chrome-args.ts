/** Build Chrome/Chromium command-line arguments for headless rendering. */

export function getChromeArgs(cacheDir: string): string[] {
  const args = [
    "--disable-gpu",
    "--enable-unsafe-swiftshader",
    "--run-all-compositor-stages-before-draw",
    "--disable-frame-rate-limit",
    "--disable-threaded-animation",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu-sandbox",
    "--disable-gpu-watchdog",
    "--disable-features=PaintHolding",
  ];
  if (cacheDir) {
    args.push(`--disk-cache-dir=${cacheDir}`);
  }
  return args;
}
