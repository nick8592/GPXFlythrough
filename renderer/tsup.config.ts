import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/bin/render.ts"],
  format: ["esm"],
  outDir: "dist/bin",
  clean: true,
  splitting: false,
  sourcemap: true,
  external: [
    "puppeteer",
    "@puppeteer/browsers",
    "ws",
    "devtools-protocol",
    "cosmiconfig",
    "yaml",
    "debug",
    "rimraf",
    "https-proxy-agent",
    "proxy-from-env",
  ],
});
