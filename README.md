# GPXFlythrough

Convert GPX tracks into interactive 3D flythrough visualizations.

## What It Does

GPXFlythrough takes your GPS recording files (`.gpx`) and produces:

- **Interactive 3D flythrough viewer** — a drone-like camera following your route over realistic terrain, with play/pause, speed control, and timeline scrubbing
- **Data overlays** — heart rate, speed, and elevation profile visualized alongside the route (coming in Phase 4)

All rendering runs **locally** — no cloud uploads, no API keys required for basic usage.

## Install

```bash
git clone https://github.com/nick8592/GPXFlythrough.git
cd GPXFlythrough
uv sync

# Set up the TypeScript renderer:
cd renderer
npm ci
cd ..
```

Requires Python 3.13+, [uv](https://docs.astral.sh/uv/), and Node.js 20+.

## Usage

```bash
# Show track summary
gpxflythrough info hike.gpx

# Parse and sanitize, export as JSON
gpxflythrough parse hike.gpx -o cleaned.json

# Export as GeoJSON
gpxflythrough parse hike.gpx -o cleaned.geojson --format geojson

# Skip sanitization
gpxflythrough parse hike.gpx -o raw.json --no-sanitize

# Open interactive 3D flythrough viewer
gpxflythrough view hike.gpx
```

### View Options

| Flag | Values | Default |
|------|--------|---------|
| `--no-terrain` | Disable terrain (flat ellipsoid) | off |
| `--no-browser` | Don't auto-open browser | off |
| `--theme` | `dark`, `light` | `dark` |
| `--speed` | `0.5`, `1`, `2`, `4` | `1` |
| `--height` | Camera height above terrain (m) | `50` |
| `--port` | Server port (0 = random) | `0` |
| `--token` | Cesium Ion access token | none |

```bash
# View without terrain (no API key needed)
gpxflythrough view hike.gpx --no-terrain

# Start at 2x speed with light theme
gpxflythrough view hike.gpx --speed 2 --theme light

# Use a specific port
gpxflythrough view hike.gpx --port 8080
```

### Example output

```
$ gpxflythrough info examples/Nangang_Ridge_Hike.gpx

                 南港山縫走                  
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property      ┃ Value                     ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Activity      │ hiking                    │
│ Segments      │ 1                         │
│ Total points  │ 5850                      │
│ Elevation min │ 20.0 m                    │
│ Elevation max │ 366.2 m                   │
│ Has HR data   │ no                        │
│ Has cadence   │ no                        │
│ Has speed     │ no                        │
│ Start time    │ 2026-07-26T07:30:34+00:00 │
└───────────────┴───────────────────────────┘
```

## Data Pipeline

GPX files go through a sanitization pipeline before rendering:

1. **Outlier removal** — points implying impossible speed (>150 km/h) are removed
2. **Timestamp gap detection** — gaps >10s between points are flagged
3. **Elevation interpolation** — missing elevations filled from neighbors
4. **Savitzky-Golay smoothing** — reduces GPS jitter while preserving path shape

Track segments are never bridged — if GPS recording was interrupted (tunnels, paused device), each segment stays separate.

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
    │ • Sanitize  │─JSON─▶• Playback UI   │
    │ • Smoothing │       │ • Camera Ctrl  │
    │ • Export    │       │ • Overlays     │
    └─────────────┘       └───────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │               │
              ┌─────▼────┐ ┌─────▼─────┐ ┌──────▼──────┐
              │ Interactive│ │ Video     │ │  Future:    │
              │  Playback  │ │  Export   │ │  Web App    │
              │ Vite+TS    │ │ (Phase 6) │ │  Next.js    │
              │  Browser   │ │           │ │  + Queue    │
              └────────────┘ └───────────┘ └─────────────┘
```

**Data Engine (Python)** — GPX parsing (`gpxpy`), GPS noise reduction (Savitzky-Golay filter), timestamp gap interpolation, and clean JSON/GeoJSON export (`orjson`).

**Render Engine (TypeScript)** — CesiumJS for 3D terrain flythrough, playback controls (play/pause, speed, seek), camera path computation, and theme support.

**Interactive Viewer** — Python serves the Vite-built static bundle with track data injected into the page. Browser opens CesiumJS globe with real-time playback controls.

## Terrain Data

3D mode uses **Copernicus DEM GLO-30** (30m resolution, ±4m vertical accuracy) for realistic terrain rendering. Terrain tiles are fetched on-demand from Cesium Ion. Use `--no-terrain` for a flat ellipsoid that doesn't require an API token.

## Roadmap

- [x] Project planning and architecture design
- [x] **Phase 0** — GPX parsing, data sanitization, CLI skeleton
- [x] **Phase 1** — Interactive 3D flythrough viewer (CesiumJS + browser playback)
- [ ] **Phase 2** — 2D map animation viewer (MapLibre)
- [ ] **Phase 3** — Data overlays (heart rate, speed, elevation profile)
- [ ] **Phase 4** — Camera configuration and visual themes
- [ ] **Phase 5** — Video export (Puppeteer + FFmpeg)
- [ ] **Phase 6** — Web app (upload, job queue, sharing)

## Example

The `examples/` directory contains `Nangang_Ridge_Hike.gpx` — a real hiking track from 南港山縱走 (Nangang Ridge Traverse) in Taipei, recorded via Strava with 5,850 trackpoints.

## Development

```bash
# Python
uv sync                          # install dependencies
uv run basedpyright src/         # type check
uv run ruff check src/           # lint
uv run ruff format --check src/  # format check
uv run pytest tests/ -v          # run tests (83 tests)

# Renderer (renderer/)
cd renderer
npm ci                           # install dependencies
npm run typecheck                # type check
npm run lint                     # lint
npm run test                     # run tests (37 tests)
npm run build                    # build
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Data Engine | Python 3.13+, gpxpy, scipy, orjson, typer, rich |
| 3D Renderer | CesiumJS |
| Interactive Playback | Vite + TypeScript |
| Terrain | Copernicus DEM GLO-30 |
| Video Export (future) | Puppeteer (CDP) → FFmpeg |
| Web App (future) | Next.js + Tailwind CSS |

## License

MIT
