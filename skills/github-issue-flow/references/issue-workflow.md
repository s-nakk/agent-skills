# Issue Workflow

## Start

1. Read the repository's agent rule file (`AGENTS.md`, `CLAUDE.md`) and any documentation index it points to
2. Confirm `gh auth status` and the repository identity with `gh repo view --json nameWithOwner`
3. Inspect the current checkout with `git status -sb`
4. If code or tracked docs will change, create a dedicated worktree from `origin/main` (or the base branch the user named). Follow the repository's worktree location rule if one exists

When the user did not specify an Issue number, list open Issues and choose the highest-priority actionable one.
Prefer the repository's priority labels (for example `priority:p0` before `priority:p1`), then incident or production labels.
Do not change selection if the user names an Issue.

## Triage

Collect current facts before editing.

```bash
gh issue view <issue-number> --json number,title,body,labels,state,url
gh pr list --state open --search "<issue-number> in:body"
```

If Project state matters, read the live GitHub Project state. Do not assume old memory is current.

Existing Issues stay read-only. Labels, Project status, comments, and state change only when the current user request names the Issue, the field, and the value.

## Implementation

Follow the repository workflow (SDD → Red → Green → Refactor).

1. Write or update the spec before implementation unless the change is UI-only
2. Add a failing regression test and run it (Red)
3. Implement the smallest fix (Green)
4. Refactor only while tests remain green
5. Run focused tests, relevant surrounding tests, full relevant project tests, build, lint / type-check, and `git diff --check`
6. After the draft PR exists, run the risk-weighted adversarial independent review (`independent-final-review`) in a separate session. Fix blockers, re-verify, push, and get a diff-only re-review of the updated head from the same reviewer

Use library documentation tools (for example Context7 MCP) for framework APIs.
Use live logs, API probes, tests, and GitHub state instead of guesses.

## Commit And PR

Stage only the intended files.
Commit message subject and body must be Japanese (technical identifiers stay in their original form).
Push the branch and create a draft PR.

Before creating a new PR, check whether the branch already has an open PR.

```bash
gh pr list --head "$(git branch --show-current)" --json number,title,isDraft,autoMergeRequest,url
```

If an existing draft PR without auto-merge exists, update it instead of creating a duplicate.
If the existing PR is ready or auto-merge is enabled, stop and ask.

Default to `gh pr create --draft`. Use a non-draft PR only when the user asks for it.

## PR Body

Use `../assets/pr-body-template.md`.
Replace placeholders with actual facts.
Keep `Refs #<issue-number>` in the body unless the user explicitly requested auto close.
Write for non-engineers by default.
Describe behavior in business language (for example `問い合わせ一覧の絞り込み`, `予約案内の表示`) instead of code identifiers when possible.
Put exact command names, file paths, method names, and error names only where they are needed for verification or developer handoff.

Do not write `対象: GitHub Issue 133`.
That text does not create GitHub linkage.
Write `Refs #133`.

Do not use `Fixes`, `Closes`, or `Resolves` by default.
Those keywords close the Issue when the PR is merged into the default branch.

## Final Checks

After PR creation or update, verify the PR and Issue linkage.

```bash
gh pr view <pr-number> --json number,title,isDraft,headRefName,baseRefName,url,body,closingIssuesReferences
gh api repos/<owner>/<repo>/issues/<issue-number>/timeline \
  -H 'Accept: application/vnd.github+json' \
  --jq '.[] | select(.event == "cross-referenced" or .event == "connected" or .event == "referenced")'
```

If the timeline does not show the reference yet, the PR body must still contain `Refs #<issue-number>`.
Report that distinction honestly.

## Completion Report

Report these facts.

- Issue number and PR URL
- Branch and commit
- What changed
- Verification commands with pass or fail results
- Independent review result (reviewed head SHA, blocker count and resolution, anything left open)
- Whether the PR is linked with `Refs #番号`
- Whether any Issue field was changed, and the user instruction that authorized it

Use non-engineer-friendly Japanese for the summary and impact.
Avoid exposing internal identifiers unless the user asks for implementation details.

If a temporary worktree was created and is clean after the review cycle, remove it with `git worktree remove <path>`.
Do not remove a dirty worktree without explicit confirmation.
