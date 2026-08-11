import { createServer } from "node:http";
import type { Server } from "node:http";

export type { Server };
import { readFile } from "node:fs/promises";
import { join, extname } from "node:path";

const MIME_TYPES: Record<string, string> = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".mjs": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".wasm": "application/wasm",
  ".ico": "image/x-icon",
  ".map": "application/json",
};

/** Start a local HTTP server serving the dist/ directory. Returns the server + port. */
export async function startStaticServer(
  distDir: string,
): Promise<{ server: Server; port: number }> {
  const server = createServer(async (req, res) => {
    const urlPath = req.url?.split("?")[0] ?? "/";
    const filePath = join(distDir, urlPath === "/" ? "index.html" : urlPath);

    try {
      const content = await readFile(filePath);
      const ext = extname(filePath);
      const contentType = MIME_TYPES[ext] ?? "application/octet-stream";
      res.writeHead(200, { "Content-Type": contentType });
      res.end(content);
    } catch {
      res.writeHead(404);
      res.end("Not found");
    }
  });

  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      const port = typeof addr === "object" && addr !== null ? addr.port : 0;
      resolve({ server, port });
    });
  });
}
