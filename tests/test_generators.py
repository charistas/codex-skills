from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_img_sources(html: str) -> list[str]:
    marker = '<img src="'
    sources: list[str] = []
    start = 0
    while True:
        index = html.find(marker, start)
        if index == -1:
            return sources
        value_start = index + len(marker)
        value_end = html.find('"', value_start)
        sources.append(html[value_start:value_end])
        start = value_end + 1


class GeneratorTests(unittest.TestCase):
    def assert_image_sources_resolve(self, output_dir: Path) -> None:
        html = (output_dir / "index.html").read_text(encoding="utf-8")
        sources = read_img_sources(html)
        self.assertGreater(len(sources), 0)
        for source in sources:
            self.assertTrue((output_dir / source).is_file(), source)

    def test_visual_diff_example_builds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "visual-diff"
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "skills/visual-diff/scripts/build_contact_sheet.py"),
                    "--manifest",
                    str(ROOT / "examples/visual-diff-manifest.json"),
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            output_lines = result.stdout.splitlines()
            self.assertEqual(str((output_dir / "index.html").resolve()), output_lines[0])
            self.assertIn("1200 x 800 PNG", result.stdout)
            self.assert_image_sources_resolve(output_dir)

    def test_screen_flow_example_builds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "screen-flow"
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "skills/screen-flow-capture/scripts/build_flow_sheet.py"),
                    "--manifest",
                    str(ROOT / "examples/screen-flow-manifest.json"),
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            output_lines = result.stdout.splitlines()
            self.assertEqual(str((output_dir / "index.html").resolve()), output_lines[0])
            self.assertIn("1200 x 800 PNG", result.stdout)
            self.assert_image_sources_resolve(output_dir)

    def test_review_once_dry_run_selects_uncommitted_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
            (repo / "README.md").write_text("# Example\n", encoding="utf-8")
            env = os.environ.copy()
            env["CODEX_BIN"] = "codex"
            result = subprocess.run(
                [str(ROOT / "skills/review-loop/scripts/review-once"), "--dry-run"],
                cwd=repo,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("review-loop target: local", result.stdout)
            self.assertIn("codex review --uncommitted", result.stdout)


if __name__ == "__main__":
    unittest.main()
