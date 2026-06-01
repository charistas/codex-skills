---
name: screen-flow-capture
description: Capture a described app flow into ordered screenshots and a shareable one-column HTML page. Use when Codex is asked to document every screen in a flow, capture a walkthrough, screenshot a feature path, capture flow screenshots, produce a flow contact sheet, make screenshot capture shareable, or show the current state of a web, iOS, macOS, desktop, or other app workflow from start to finish. The deliverable must include index.html, not only raw screenshots.
---

# Screen Flow Capture

Capture the requested product flow as an ordered visual walkthrough. The skill is platform-agnostic: use the capture tools appropriate to the current app, then generate a single-column HTML artifact from the screenshots.

## Completion Contract

Do not stop after capturing screenshots. A task using this skill is incomplete until it produces:

- An ordered screenshot set.
- A generated `index.html` flow sheet.
- Native/high-resolution source images, preferably PNG.
- A dimension/format check for every screenshot.
- A final path to the HTML page.
- A note covering any omitted screens or branches.

## Capture Quality Contract

Default to share-ready captures, not quick review thumbnails.

- Capture native-resolution PNGs unless the user explicitly asks for compressed or low-resolution images.
- Do not use resized previews, thumbnails, JPEG exports, or browser-displayed screenshots as source images.
- Do not downsample or recompress screenshots before building the HTML.
- For iOS Simulator, prefer native simulator PNGs at device pixel resolution, not scaled `369 x 800` JPEGs.
- For web and desktop apps, capture at the actual viewport/window pixel resolution; use PNG where the tool supports it.
- Before handoff, verify dimensions and format with `build_flow_sheet.py` or another concrete image probe.
- If the generator reports low-res or lossy images, recapture. Only pass `--allow-low-res` or `--allow-lossy` when the user explicitly chose that tradeoff.

## Workflow

1. Define the flow scope.
   - Parse the user's requested flow and name the entry point, exit point, and major branches.
   - Include the primary path plus visible options, sheets, modals, empty states, and error/permission states that are naturally part of the requested flow.
   - Treat "all options" as "all meaningful user-visible branches reachable in the local environment." Do not invent unavailable states.
   - Ask a brief clarification only when the flow boundary is ambiguous enough to risk capturing the wrong feature.

2. Plan capture steps before launching the app.
   - List the screens to capture in likely order.
   - Identify required seed data, account state, feature flags, viewport/device, and environment limitations.
   - Respect repository instructions for build, simulator, browser, desktop app, cleanup, and artifact storage.
   - Store screenshots outside the repo by default under `/private/tmp/<app>-flow-<date>-<topic>`.

3. Capture with the platform's safest workflow.
   - Web apps: use the in-app browser or Playwright, capture full-page or viewport PNGs as appropriate.
   - iOS apps: use the repo's simulator/toolchain-lock rules before build, launch, navigation, native PNG screenshot, and cleanup.
   - macOS/desktop apps: use the repo's run/debug guidance and capture the relevant windows as PNGs when available.
   - Existing screenshot folders: skip recapture and build the HTML from those images.
   - Keep filenames ordered and descriptive, for example `01-entry.png`, `02-options-expanded.png`.

4. Track coverage while capturing.
   - Record each screenshot title, note, and file path.
   - If a branch cannot be captured, include a short omitted item in the final handoff with the reason.
   - Avoid destructive, paid, externally transmitting, or account-changing actions unless the user explicitly approved them.

5. Generate the flow HTML.
   - Create a manifest JSON matching the format below.
   - Run `scripts/build_flow_sheet.py`.
   - Verify all image references resolve.
   - Open the HTML when the available browser/tool policy allows; otherwise report the path.

## Manifest Format

Use absolute image paths when possible. Relative image paths resolve from the manifest file's directory.

```json
{
  "title": "Check-In Flow",
  "subtitle": "Current app flow capture",
  "meta": ["Build: local main", "Device: iPhone 16"],
  "quality": {
    "min_short_edge": 700,
    "min_long_edge": 1000,
    "allow_low_res": false,
    "allow_lossy": false
  },
  "screens": [
    {
      "title": "Entry Point",
      "note": "Home with check-in button visible",
      "image": "/private/tmp/app-flow/01-entry.png"
    },
    {
      "title": "Options Expanded",
      "note": "All optional controls visible",
      "image": "/private/tmp/app-flow/02-options-expanded.png"
    }
  ],
  "omitted": [
    "Health permission prompt not available in Simulator."
  ]
}
```

## Script

Run from the skill directory or pass the absolute script path:

```bash
python3 scripts/build_flow_sheet.py --manifest /private/tmp/flow.json --output-dir /private/tmp/app-flow-sheet
```

By default, the script rejects JPEG screenshots and images below `700` px on the short edge or `1000` px on the long edge. These defaults catch scaled mobile thumbnails such as `369 x 800` while allowing native mobile, desktop, and high-DPR web captures.

Optional overrides:

```bash
python3 scripts/build_flow_sheet.py \
  --manifest /private/tmp/flow.json \
  --output-dir /private/tmp/app-flow-sheet \
  --title "Insights Flow" \
  --subtitle "All locally reachable Insights screens"
```

Only use explicit opt-outs for intentional low-quality artifacts:

```bash
python3 scripts/build_flow_sheet.py \
  --manifest /private/tmp/flow.json \
  --output-dir /private/tmp/app-flow-sheet \
  --allow-low-res \
  --allow-lossy
```

The script copies referenced images into `assets/` inside the output directory and writes `index.html`. Report the final HTML path as the deliverable.

## Verification

Before handoff:

- Confirm the output folder contains `index.html` and copied images.
- Verify every `<img src="...">` in the HTML resolves to an existing file.
- Report screenshot dimensions/formats from the generator output.
- If browser verification is possible, inspect that screenshots are visible, ordered correctly, and readable.
- State what was captured, what was omitted, and why.
- Clean up app/build/simulator/browser processes started for the capture unless the user asked to keep them running.
