---
name: visual-diff
description: Create local HTML contact sheets for visual UI review from screenshots. Use when Codex is asked to compare before/after screens, show app changes side by side, leave empty cells for removed or newly added screens, generate an after-only share page, or package screenshots from web, iOS Simulator, macOS app, or existing image folders into a reviewable HTML artifact. The deliverable must use native/high-resolution images by default and include index.html, not only raw screenshots.
---

# Visual Diff Contact Sheet

Build a self-contained HTML page from UI screenshots so a user can review visual changes quickly. The reusable part is screenshot organization and HTML generation; screenshot capture depends on the app platform and repository instructions.

## Completion Contract

Do not stop after capturing or collecting screenshots. A task using this skill is incomplete until it produces:

- An ordered screenshot set for the requested comparison or after-only page.
- Native/high-resolution source images, preferably PNG.
- A generated `index.html` contact sheet.
- A dimension/format check for every screenshot.
- A final path to the HTML page.
- A note covering any unmatched, removed, added, or omitted screens.

## Capture Quality Contract

Default to share-ready captures, not quick review thumbnails.

- Capture native-resolution PNGs unless the user explicitly asks for compressed or low-resolution images.
- Do not use resized previews, thumbnails, JPEG exports, browser-displayed screenshots, or copied UI thumbnails as source images.
- Do not downsample or recompress screenshots before building the HTML.
- For iOS Simulator, prefer native simulator PNGs at device pixel resolution, not scaled `369 x 800` JPEGs.
- For web and desktop apps, capture at the actual viewport/window pixel resolution; use PNG where the tool supports it.
- Before handoff, verify dimensions and format with `build_contact_sheet.py` or another concrete image probe.
- If the generator reports low-res or lossy images, recapture. Only pass `--allow-low-res` or `--allow-lossy` when the user explicitly chose that tradeoff.

## Workflow

1. Determine the comparison shape.
   - Use `comparison` mode for before/after pages.
   - Use `after-only` mode when the user wants to share the current state only.
   - If the user names a prior comparison or baseline, reuse those `before` screenshots instead of recapturing.

2. Protect local work before capturing a previous revision.
   - Run `git status -sb` and inspect whether the worktree is dirty.
   - Prefer a temporary git worktree for the before ref: `git worktree add /private/tmp/<task>-before <ref>`.
   - Only checkout a previous revision in the current worktree when the user explicitly asks for that and the worktree is clean or safely stashed.
   - Never discard unrelated user changes.

3. Capture or collect screenshots.
   - Existing images: use them directly.
   - Web apps: use the browser or Playwright workflow appropriate to the repo and capture full-page or viewport PNGs.
   - iOS apps: follow the repo's iOS Simulator/toolchain-lock instructions before build, launch, navigation, native PNG screenshots, or cleanup.
   - macOS apps: use the repo's macOS build/run guidance and capture the relevant windows as PNGs when available.
   - Keep task artifacts outside the repo by default, under `/private/tmp/<descriptive-name>`.

4. Match screens by stable ordered labels.
   - Use the same title for corresponding before and after states.
   - Keep filenames ordered with numeric prefixes, for example `01-welcome.jpg`.
   - When a screen exists on only one side, include the image on that side and an empty placeholder on the other.
   - Do not pretend unmatched screens are equivalent just because their order is similar.

5. Generate the HTML using the bundled script.
   - Create a manifest JSON file.
   - Run `scripts/build_contact_sheet.py`.
   - Verify all image references resolve.
   - Open the HTML if the browser/tool policy allows it; otherwise report the path.

## Manifest Format

Use absolute image paths when possible. Relative image paths resolve from the manifest file's directory.

Comparison:

```json
{
  "mode": "comparison",
  "title": "App Onboarding Before and After",
  "subtitle": "Current UI review",
  "before_label": "Before",
  "after_label": "After",
  "meta": ["Before: abc123", "After: def456"],
  "quality": {
    "min_short_edge": 700,
    "min_long_edge": 1000,
    "allow_low_res": false,
    "allow_lossy": false
  },
  "screens": [
    {
      "title": "Welcome",
      "note": "First launch",
      "before": "/private/tmp/before/01-welcome.jpg",
      "after": "/private/tmp/after/01-welcome.jpg"
    },
    {
      "title": "Removed Setup Step",
      "before": "/private/tmp/before/02-setup.jpg",
      "after": null,
      "empty_after": "Removed in the current flow."
    }
  ]
}
```

After-only:

```json
{
  "mode": "after-only",
  "title": "Current Onboarding Screens",
  "subtitle": "Shareable review set",
  "meta": ["After: def456"],
  "quality": {
    "min_short_edge": 700,
    "min_long_edge": 1000,
    "allow_low_res": false,
    "allow_lossy": false
  },
  "screens": [
    {
      "title": "Welcome",
      "note": "First launch",
      "image": "/private/tmp/after/01-welcome.jpg"
    }
  ]
}
```

## Script

Run from the skill directory or pass the absolute script path:

```bash
python3 scripts/build_contact_sheet.py --manifest /private/tmp/screens.json --output-dir /private/tmp/app-visual-diff
```

By default, the script rejects JPEG screenshots and images below `700` px on the short edge or `1000` px on the long edge. These defaults catch scaled mobile thumbnails such as `369 x 800` while allowing native mobile, desktop, and high-DPR web captures.

Optional overrides:

```bash
python3 scripts/build_contact_sheet.py \
  --manifest /private/tmp/screens.json \
  --output-dir /private/tmp/app-visual-diff \
  --title "Checkout Flow Before and After" \
  --subtitle "Desktop and mobile captures"
```

Only use explicit opt-outs for intentional low-quality artifacts:

```bash
python3 scripts/build_contact_sheet.py \
  --manifest /private/tmp/screens.json \
  --output-dir /private/tmp/app-visual-diff \
  --allow-low-res \
  --allow-lossy
```

The script copies referenced images into `assets/` inside the output directory and writes `index.html`. Report the final HTML path as the deliverable.

## Verification

Before handoff:

- Confirm the output folder contains `index.html` and copied images.
- Verify every `<img src="...">` in the HTML resolves to an existing file.
- Report screenshot dimensions/formats from the generator output.
- If visual browser verification is possible, open the page and inspect that rows/cards are readable and screenshots are not broken.
- If browser verification is blocked, state that and report the filesystem checks that passed.
