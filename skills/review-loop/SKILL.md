---
name: review-loop
description: "Run a bounded Codex review/fix/re-review loop for current local work. Use when the user asks for repeated Codex review, review-loop closeout, fixes for accepted review findings, or a sanity-check of findings before changing code."
---

# Review Loop

Run a sequential local review closeout loop on the current checkout. Keep the work small and reviewable.

Do not spawn subagents, create worktrees, run tests in parallel with review, start extra simulators, or commit, stash, or push merely to change review targets unless the user explicitly asks.

## Defaults

- Run at most 3 `codex review` invocations total, including retries and all review targets. Ask before exceeding the cap.
- Treat review output as advisory. Verify each finding in the real code path before editing.
- Prefer localized root-cause fixes. Reject speculative edge cases, style churn, and broad rewrites.

## Target Selection

Use the smallest targets that cover all current work:

1. Review dirty and untracked work with `codex review --uncommitted`.
2. Review committed branch work against its actual integration base with `codex review --base <base>`.
3. Use `codex review --commit <sha>` only when the user wants one commit reviewed or no broader branch delta is intended.

For the comparison base, prefer an explicit `--base`. Otherwise use the tracking remote's default branch, such as `origin/HEAD`. Never treat a feature branch's same-name tracking ref as its integration base.

When dirty and committed work both exist, finish the uncommitted phase and then run the base phase. The tree does not need to become clean between phases; do not commit or stash just for review. The uncommitted phase covers untracked files, while the base phase provides the cumulative tracked branch diff.

Use the bundled helper to inspect or run one target:

```bash
~/.codex/skills/review-loop/scripts/review-once --dry-run
~/.codex/skills/review-loop/scripts/review-once
```

Use `--mode local`, `--mode base`, or `--mode commit` for an explicit target. Use repeatable `--config KEY=VALUE` for narrow Codex configuration overrides. Save output only to an absolute path outside the Git worktree.

## Loop

Before review:

1. Record `git status` and run one cheap baseline verification when the touched scope has an obvious command.
2. Run the helper with `--dry-run`. Record the selected target and whether its note identifies a second base phase.

For each review invocation, up to the hard cap:

1. Run the selected review. Record Git status before and after; the helper warns if tracked or untracked state changes.
2. If review fails, retry once only when the failure is clearly transient. Otherwise stop and report the exact command and first relevant error.
3. Sanity-check each finding: root cause, accepted/rejected/needs-user-decision, proposed fix, regression risk, and verification plan. Treat a real verification failure as actionable even when review did not report it.
4. Fix accepted findings only. Do not make a judgment-dependent change; independent safe fixes may proceed.
5. Run focused verification for the changed scope.
6. Re-review the same target after fixes, or advance to the pending base phase when the current phase has no accepted findings.

At closeout, run the full relevant local verification gate once when it is available and runnable. A failing test needs investigation; a missing dependency, unavailable service, or environment limitation is a verification block.

Stop when all planned targets have no accepted findings, the review cap is reached, verification is blocked, review cannot run, or user judgment is required.

## Reporting

Report:

- review targets and commands used
- accepted fixes, rejected findings, and pending user decisions
- focused and final verification results
- whether the final review was clean, or the exact stop reason

For a review or verification block, include the exact command and first relevant error line.
