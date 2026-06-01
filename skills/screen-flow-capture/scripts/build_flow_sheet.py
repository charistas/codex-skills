#!/usr/bin/env python3
"""Build a one-column HTML screen-flow sheet from a JSON manifest."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_MIN_SHORT_EDGE = 700
DEFAULT_MIN_LONG_EDGE = 1000


@dataclass(frozen=True)
class ImageInfo:
    format: str
    width: int | None
    height: int | None

    @property
    def dimensions_label(self) -> str:
        if self.width is None or self.height is None:
            return "unknown size"
        return f"{self.width} x {self.height}"

    @property
    def format_label(self) -> str:
        return self.format.upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to manifest JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory for index.html and copied assets.")
    parser.add_argument("--title", help="Override page title.")
    parser.add_argument("--subtitle", help="Override page subtitle.")
    parser.add_argument(
        "--min-short-edge",
        type=int,
        help=f"Minimum short image edge in pixels. Defaults to manifest quality.min_short_edge or {DEFAULT_MIN_SHORT_EDGE}.",
    )
    parser.add_argument(
        "--min-long-edge",
        type=int,
        help=f"Minimum long image edge in pixels. Defaults to manifest quality.min_long_edge or {DEFAULT_MIN_LONG_EDGE}.",
    )
    parser.add_argument(
        "--allow-low-res",
        action="store_true",
        help="Allow images below the minimum pixel dimensions.",
    )
    parser.add_argument(
        "--allow-lossy",
        action="store_true",
        help="Allow lossy screenshot formats such as JPEG.",
    )
    return parser.parse_args()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "screen"


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Manifest root must be a JSON object.")
    screens = data.get("screens")
    if not isinstance(screens, list) or not screens:
        raise ValueError("Manifest must contain a non-empty 'screens' array.")
    return data


def resolve_source(value: str, manifest_dir: Path) -> Path:
    source = Path(value).expanduser()
    if not source.is_absolute():
        source = manifest_dir / source
    if not source.is_file():
        raise FileNotFoundError(f"Image not found: {source}")
    return source


def read_image_info(path: Path) -> ImageInfo:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        return ImageInfo("png", width, height)

    if data.startswith(b"\xff\xd8"):
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            while index < len(data) and data[index] == 0xFF:
                index += 1
            if index >= len(data):
                break
            marker = data[index]
            index += 1
            if marker in {0x01, 0xD9} or 0xD0 <= marker <= 0xD7:
                continue
            if index + 2 > len(data):
                break
            length = int.from_bytes(data[index:index + 2], "big")
            if length < 2 or index + length > len(data):
                break
            segment = index + 2
            if marker in {
                0xC0, 0xC1, 0xC2, 0xC3,
                0xC5, 0xC6, 0xC7,
                0xC9, 0xCA, 0xCB,
                0xCD, 0xCE, 0xCF,
            } and segment + 5 <= len(data):
                height = int.from_bytes(data[segment + 1:segment + 3], "big")
                width = int.from_bytes(data[segment + 3:segment + 5], "big")
                return ImageInfo("jpeg", width, height)
            index += length
        return ImageInfo("jpeg", None, None)

    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        if len(data) >= 10:
            width = int.from_bytes(data[6:8], "little")
            height = int.from_bytes(data[8:10], "little")
            return ImageInfo("gif", width, height)
        return ImageInfo("gif", None, None)

    suffix = path.suffix.lower().lstrip(".") or "unknown"
    return ImageInfo(suffix, None, None)


def copy_image(value: str, manifest_dir: Path, assets_dir: Path, index: int, title: str) -> tuple[str, ImageInfo]:
    source = resolve_source(value, manifest_dir)
    image_info = read_image_info(source)
    suffix = source.suffix.lower() or ".png"
    destination_name = f"{index:02d}-{slugify(title)}{suffix}"
    destination = assets_dir / destination_name
    shutil.copy2(source, destination)
    return f"assets/{destination_name}", image_info


def quality_failures(
    *,
    image_path: str,
    image_info: ImageInfo,
    min_short_edge: int,
    min_long_edge: int,
    allow_low_res: bool,
    allow_lossy: bool,
) -> list[str]:
    failures: list[str] = []
    if image_info.format == "jpeg" and not allow_lossy:
        failures.append(f"{image_path}: JPEG is lossy; capture native PNG or pass --allow-lossy if intentional.")
    if not allow_low_res:
        if image_info.width is None or image_info.height is None:
            failures.append(f"{image_path}: could not read image dimensions; verify manually or pass --allow-low-res.")
        else:
            short_edge = min(image_info.width, image_info.height)
            long_edge = max(image_info.width, image_info.height)
            if short_edge < min_short_edge or long_edge < min_long_edge:
                failures.append(
                    f"{image_path}: {image_info.dimensions_label} is below "
                    f"{min_short_edge} short-edge / {min_long_edge} long-edge minimum."
                )
    return failures


def render_meta(meta: list[Any]) -> str:
    if not meta:
        return ""
    pills = "\n".join(f'      <span class="pill">{escape(item)}</span>' for item in meta)
    return f'    <div class="meta">\n{pills}\n    </div>'


def render_omitted(omitted: list[Any]) -> str:
    if not omitted:
        return ""
    items = "\n".join(f"        <li>{escape(item)}</li>" for item in omitted)
    return f"""    <section class="omitted">
      <h2>Not Captured</h2>
      <ul>
{items}
      </ul>
    </section>"""


def render_screen(index: int, screen: dict[str, Any], image_src: str, image_info: ImageInfo) -> str:
    title = str(screen.get("title") or f"Screen {index}")
    note = screen.get("note")
    note_html = f'          <p class="screen-note">{escape(note)}</p>\n' if note else ""
    quality_label = f"{image_info.dimensions_label} {image_info.format_label}"
    return f"""      <section class="screen">
        <div class="screen-header">
          <div>
            <h2>{escape(title)}</h2>
{note_html}          </div>
          <div class="screen-badges">
            <span class="screen-quality">{escape(quality_label)}</span>
            <span class="screen-number">{index:02d}</span>
          </div>
        </div>
        <div class="shot-wrap">
          <img src="{escape(image_src)}" alt="{escape(title)}" loading="lazy">
        </div>
      </section>"""


def base_css() -> str:
    return """    :root {
      color-scheme: light;
      --bg: #f6f2ea;
      --panel: #fffaf2;
      --ink: #221f1c;
      --muted: #70685f;
      --line: #d8cec1;
      --accent: #2f6655;
      --accent-soft: #e4eee9;
      --warn-soft: #f2ead8;
      --shadow: rgba(35, 31, 32, 0.12);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    header,
    main {
      width: min(100%, 900px);
      margin: 0 auto;
      padding-inline: 24px;
    }

    header {
      padding-top: 34px;
      padding-bottom: 18px;
    }

    h1 {
      margin: 0 0 10px;
      font-size: clamp(30px, 5vw, 48px);
      line-height: 1.05;
      letter-spacing: 0;
    }

    .subtitle {
      max-width: 720px;
      margin: 0;
      color: var(--muted);
      font-size: 16px;
    }

    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
      color: var(--muted);
      font-size: 13px;
    }

    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 10px;
      background: rgba(255, 255, 255, 0.58);
    }

    main {
      padding-top: 8px;
      padding-bottom: 56px;
    }

    .flow {
      display: grid;
      gap: 24px;
    }

    .screen,
    .omitted {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      overflow: hidden;
    }

    .screen-header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.5);
    }

    .screen-header h2,
    .omitted h2 {
      margin: 0;
      font-size: 17px;
      line-height: 1.25;
      letter-spacing: 0;
    }

    .screen-note {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 13px;
    }

    .screen-number {
      flex: 0 0 auto;
      border-radius: 999px;
      padding: 2px 8px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      line-height: 1.5;
    }

    .screen-badges {
      display: flex;
      flex: 0 0 auto;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
    }

    .screen-quality {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 8px;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.55);
      font-size: 12px;
      line-height: 1.5;
    }

    .shot-wrap {
      display: flex;
      justify-content: center;
      padding: 18px;
    }

    img {
      display: block;
      width: min(100%, 430px);
      height: auto;
      border: 1px solid #b8aea2;
      border-radius: 8px;
      background: #fff;
      box-shadow: 0 12px 28px var(--shadow);
    }

    .omitted {
      padding: 16px 18px;
      background: var(--warn-soft);
    }

    .omitted ul {
      margin: 8px 0 0;
      padding-left: 20px;
      color: var(--muted);
    }

    @media (max-width: 720px) {
      header,
      main {
        padding-inline: 14px;
      }

      header {
        padding-top: 24px;
      }

      .screen-header {
        display: block;
        padding-inline: 14px;
      }

      .screen-badges {
        justify-content: flex-start;
      }

      .screen-number,
      .screen-quality {
        display: inline-block;
        margin-top: 6px;
      }

      .shot-wrap {
        padding: 14px;
      }
    }"""


def render_page(
    *,
    title: str,
    subtitle: str,
    meta: list[Any],
    sections_html: str,
    omitted_html: str,
) -> str:
    subtitle_html = f'    <p class="subtitle">{escape(subtitle)}</p>\n' if subtitle else ""
    meta_html = render_meta(meta)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
{base_css()}
  </style>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
{subtitle_html}{meta_html}
  </header>

  <main>
    <div class="flow">
{sections_html}
    </div>
{omitted_html}
  </main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    manifest = load_manifest(manifest_path)

    title = args.title or str(manifest.get("title") or "Screen Flow Capture")
    subtitle = args.subtitle if args.subtitle is not None else str(manifest.get("subtitle") or "")
    meta = manifest.get("meta") or []
    omitted = manifest.get("omitted") or []
    if not isinstance(meta, list):
        raise ValueError("'meta' must be an array when present.")
    if not isinstance(omitted, list):
        raise ValueError("'omitted' must be an array when present.")
    quality = manifest.get("quality") or {}
    if not isinstance(quality, dict):
        raise ValueError("'quality' must be an object when present.")
    min_short_edge = args.min_short_edge
    if min_short_edge is None:
        min_short_edge = int(quality.get("min_short_edge", DEFAULT_MIN_SHORT_EDGE))
    min_long_edge = args.min_long_edge
    if min_long_edge is None:
        min_long_edge = int(quality.get("min_long_edge", DEFAULT_MIN_LONG_EDGE))
    allow_low_res = bool(args.allow_low_res or quality.get("allow_low_res", False))
    allow_lossy = bool(args.allow_lossy or quality.get("allow_lossy", False))

    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir = manifest_path.parent

    sections: list[str] = []
    failures: list[str] = []
    image_summaries: list[str] = []
    for index, raw_screen in enumerate(manifest["screens"], start=1):
        if not isinstance(raw_screen, dict):
            raise ValueError(f"Screen {index} must be an object.")
        screen = raw_screen
        title_for_file = str(screen.get("title") or f"Screen {index}")
        image_value = screen.get("image")
        if not image_value:
            raise ValueError(f"Screen {index} must contain 'image'.")
        source_path = str(image_value)
        image_src, image_info = copy_image(source_path, manifest_dir, assets_dir, index, title_for_file)
        failures.extend(
            quality_failures(
                image_path=source_path,
                image_info=image_info,
                min_short_edge=min_short_edge,
                min_long_edge=min_long_edge,
                allow_low_res=allow_low_res,
                allow_lossy=allow_lossy,
            )
        )
        image_summaries.append(f"{index:02d} {title_for_file}: {image_info.dimensions_label} {image_info.format_label}")
        sections.append(render_screen(index, screen, image_src, image_info))

    if failures:
        for failure in failures:
            print(f"quality error: {failure}", file=sys.stderr)
        print(
            "quality error: recapture native-resolution PNGs, or explicitly pass "
            "--allow-low-res/--allow-lossy only when the user asked for compressed or small images.",
            file=sys.stderr,
        )
        return 2

    html_output = render_page(
        title=title,
        subtitle=subtitle,
        meta=meta,
        sections_html="\n\n".join(sections),
        omitted_html=render_omitted(omitted),
    )
    output_path = output_dir / "index.html"
    output_path.write_text(html_output, encoding="utf-8")
    print(output_path)
    for summary in image_summaries:
        print(summary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
