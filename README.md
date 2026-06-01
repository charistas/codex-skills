# Codex Skills

A personal collection of practical Codex skills for review, visual QA, automation, and agent workflows. The collection currently starts with:

- `review-loop`: run a bounded `codex review` / fix / verify / re-review loop.
- `screen-flow-capture`: capture a product flow into an ordered screenshot walkthrough.
- `visual-diff`: turn before/after UI screenshots into a reviewable HTML contact sheet.

These skills are intended to be copied into a Codex skills directory, for example:

```bash
cp -R skills/review-loop ~/.codex/skills/
cp -R skills/screen-flow-capture ~/.codex/skills/
cp -R skills/visual-diff ~/.codex/skills/
```

## Requirements

- Codex with skill support.
- Python 3.10+ for the screenshot HTML generators.
- Git for `review-loop`.
- Codex CLI with `codex review` for `review-loop`.

No third-party Python packages are required.

## Layout

```text
skills/
  review-loop/
  screen-flow-capture/
  visual-diff/
examples/
  fixtures/
  screen-flow-manifest.json
  visual-diff-manifest.json
tests/
  test_generators.py
```

## Smoke Tests

```bash
python3 -m unittest discover -s tests
```

The tests build HTML artifacts in temporary directories and verify that generated image references resolve.
