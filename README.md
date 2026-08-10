# GPXFlythrough

Convert GPX tracks into 2D/3D visualization videos and interactive playback.

## What It Does

GPXFlythrough takes your GPS recording files (`.gpx`) and produces:

- **3D cinematic flythrough video** — a drone-like camera following your route over realistic terrain
- **2D animated map video** — your path drawing across a flat map with auto-follow camera
- **Interactive browser playback** — watch the flythrough in-browser with play/pause, speed control, and timeline scrubbing
- **Data overlays** — heart rate, speed, and elevation profile visualized alongside the route

All rendering runs **locally** — no cloud uploads, no API keys required for basic usage.

## Quick Start

```bash
# Install (coming soon)
pip install gpxflythrough

# Parse and sanitize a GPX file
gpxflythrough parse hike.gpx -o cleaned.json

# Render 3D flythrough video
gpxflythrough render hike.gpx -o output.mp4 --mode 3d --resolution 1080p

# Render 2D map animation
gpxflythrough render hike.gpx -o output.mp4 --mode 2d --resolution 1080p

# Interactive browser preview
gpxflythrough preview hike.gpx
```

## Camera Modes

| Mode | Description |
|------|-------------|
| `follow` | First-person camera following the path at ground level |
| `birdseye` | Top-down overview tracking the path from above |
| `cinematic` | Smooth spline-based camera with easing and transitions |
| `orbit` | Camera orbiting around points of interest |

```bash
gpxflythrough render hike.gpx -o output.mp4 --camera cinematic --height 80
```

## Output Options

| Flag | Values | Default |
|------|--------|---------|
| `--mode` | `2d`, `3d` | `3d` |
| `--resolution` | `720p`, `1080p`, `4k` | `1080p` |
| `--fps` | 24, 30, 60 | 30 |
| `--camera` | `follow`, `birdseye`, `cinematic`, `orbit` | `follow` |
| `--overlays` | `hr`, `speed`, `elevation`, `none` | `elevation` |
| `--theme` | `light`, `dark`, `transparent` | `dark` |

## Architecture

```
┌──────────────────────────────────────────────┐
│                  CLI / Web API                │
└──────────┬──────────────────────┬────────────┘
           │                      │
    ┌──────▼──────┐       ┌───────▼────────┐
    │  Python     │       │  TypeScript    │
    │  Data Engine│       │  Render Engine │
    │             │       │                │
    │ • GPX Parse │       │ • CesiumJS 3D  │
    │ • Sanitize  │─JSON─▶• MapLibre 2D   │
    │ • Smoothing │       │ • Overlays     │
    │ • Export    │       │ • Camera Ctrl  │
    └─────────────┘       └───────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │               │
              ┌─────▼────┐ ┌─────▼─────┐ ┌──────▼──────┐
              │  Video   │ │ Interactive│ │  Future:    │
              │  Export   │ │  Playback  │ │  Web App    │
              │ Puppeteer│ │  Vite+TS   │ │  Next.js    │
              │ → FFmpeg  │ │  Browser   │ │  + Queue    │
              └──────────┘ └────────────┘ └─────────────┘
```

**Data Engine (Python)** — GPX parsing, GPS noise reduction (Kalman filter), timestamp gap interpolation, and clean JSON export.

**Render Engine (TypeScript)** — CesiumJS for 3D terrain flythrough, MapLibre GL for 2D map animation, overlay rendering, and camera path computation.

**Video Pipeline** — Deterministic frame-by-frame headless capture via Puppeteer, piped to FFmpeg for H.264 encoding. No dropped frames.

## Terrain Data

3D mode uses **Copernicus DEM GLO-30** (30m resolution, ±4m vertical accuracy) for realistic terrain rendering. Terrain tiles are fetched on-demand and cached locally for repeated renders.

## Roadmap

- [x] Project planning and architecture design
- [ ] **Phase 0** — GPX parsing, data sanitization, CLI skeleton
- [ ] **Phase 1** — 3D flythrough video export (CesiumJS + FFmpeg)
- [ ] **Phase 2** — 2D map animation video export (MapLibre + FFmpeg)
- [ ] **Phase 3** — Interactive browser playback (2D + 3D)
- [ ] **Phase 4** — Data overlays (heart rate, speed, elevation profile)
- [ ] **Phase 5** — Camera configuration and visual themes
- [ ] **Phase 6** — Web app (upload, job queue, sharing)

## Example

The `examples/` directory contains `Nangang_Ridge_Hike.gpx` — a real hiking track from 南港山縱走 (Nangang Ridge Traverse) in Taipei, recorded via Strava with 23K+ trackpoints.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Data Engine | Python 3.13+, gpxpy, scipy, pykalman |
| 3D Renderer | CesiumJS |
| 2D Renderer | MapLibre GL JS |
| Terrain | Copernicus DEM GLO-30 |
| Video Export | Puppeteer (CDP) → FFmpeg |
| Interactive Playback | Vite + TypeScript |
| Web App (future) | Next.js + Tailwind CSS |

## License

MIT
