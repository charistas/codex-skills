---
name: review-loop
description: "Run a bounded Codex review/fix/re-review loop for current local work. Use when the user asks for repeated Codex review, review-loop closeout, fix accepted review findings, or says to sanity-check review findings before changing code."
---

# Review Loop

Run a sequential local review closeout loop. This skill is optimized for solo development on the current checkout.

Do not spawn subagents, create worktrees, run tests in parallel with review, or start extra simulators unless the user explicitly asks.

## Defaults

- Maximum review/fix iterations: 3.
- Continue past 3 only if remaining findings are clearly actionable, fixes are localized, verification is still runnable, and scope is not drifting into broad refactoring.
- Treat `codex review` output as advisory. Verify each finding in the real code path before editing.
- Prefer small root-cause fixes at the right ownership boundary.
- Reject speculative edge cases, style churn, broad rewrites, and fixes that add more complexity than the bug justifies.

## Target Selection

Use the smallest useful review target:

1. Dirty worktree: `codex review --uncommitted`
2. Clean tree with local commits ahead of upstream/base: `codex review --base <upstream-or-base>`
3. Clean tree with no obvious base delta: `codex review --commit HEAD`

If both committed local work and dirty changes exist, review dirty changes first. After fixing dirty findings and the tree is clean, run a base or commit review so committed work is not skipped.

The bundled helper can choose the review target:

```bash
scripts/review-once --dry-run
scripts/review-once
```

Run those commands from the installed skill directory, or use the absolute path to `review-once`.
Use `--mode local`, `--mode base`, or `--mode commit` when the user specifies the target.

## Loop

For each iteration:

1. Run known cheap verification first when the touched scope has an obvious command.
2. Run `codex review` using the selected target.
3. Before changing code, sanity-check every review finding:
   - root cause
   - decision: accepted, rejected, or needs user decision
   - proposed fix
   - regression risk
   - verification plan
4. If missing context or a product/design/security decision is needed, stop and ask the user.
5. Fix accepted findings only.
6. Rerun focused verification for the touched scope.
7. Rerun review.

Stop when:

- no accepted actionable findings remain
- only rejected findings remain
- maximum iterations is reached
- verification is blocked
- a finding needs user judgment

## Reporting

In the final handoff, include:

- review command or helper invocation used
- accepted findings and fixes
- rejected findings with brief reasons
- verification commands and results
- whether the final review was clean, or why the loop stopped

If verification is blocked, report the exact command and the first relevant error line.
