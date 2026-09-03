---
name: github-issue-flow
description: GitHub Issue を起点に作業する時に使う。open Issue の選定、triage、実装、明示的に依頼された Issue field の変更、PR と Issue の紐づけ、PR 本文作成、完了報告を含む。既存 Issue は現在の依頼で対象 Issue と変更内容が名指しされた場合を除き不変とし、worktree 分離、SDD/TDD、検証、独立レビュー、日本語 commit message、draft PR 作成、非エンジニア向けの日本語、技術識別子の最小化を強制する。「GitHub Issue」「Issues」「Issue 番号」「課題を解決」「チケット対応」「Issue に紐づく PR」と言われた時に使う。
---

# GitHub Issue Flow

## Core Rules

Use this skill whenever the user says GitHub Issue, Issues, Issue 番号, 課題を解決, チケット対応, or asks to link a PR to an Issue.

Read the repository's agent rule file (`AGENTS.md`, `CLAUDE.md`) first. When it defines Issue, worktree, review, or push rules, those override the defaults below.

Hard rules. The existing-Issue immutability gate overrides every later workflow step.

- Treat every Issue as read-only immediately after its create call returns an Issue number or URL
- Do not change an existing Issue's title, body, comments, labels, assignees, milestone, state, pin, lock, transfer, Project item, or Project fields unless the user explicitly identifies the Issue and requested field or operation in the current conversation
- Do not infer Issue-mutation permission from requests to investigate, implement, resolve, complete, create a PR, or create an Issue before doing the work
- Treat Issue creation as a single create call. Do not edit the new Issue after creation to add findings, acceptance criteria, progress, corrections, or links
- Before any Issue mutation, quote three items from the current user request: target Issue, target field or operation, and requested value or purpose. If any item is missing, stop the mutation and remain read-only
- Apply this gate to CLI, REST, GraphQL, connectors, browsers, and automation. Do not bypass it through `gh api`, `updateIssue`, label or Project mutations, comments, close/reopen calls, or another tool surface
- Use `Refs #番号` by default. Use `Closes`, `Fixes`, or `Resolves` only when the user explicitly requests automatic closure of that exact Issue in the current conversation
- Put findings, scope refinements, progress, validation, and completion details in the PR body and completion report
- When the user explicitly requests restoration, recover the evidence-backed prior value, change only the requested field, then verify Issue state and Project status separately
- Work in a dedicated clean worktree for tracked or intended project files. Never edit the main checkout directly
- Follow the repo workflow: SDD → Red → Green → Refactor → verification → scoped commit → push → draft PR → independent review (`independent-final-review`)
- Write commit messages in Japanese, keeping technical identifiers unchanged
- Write PR bodies, Issue-facing text, and completion reports for non-engineers by default. If a Japanese writing skill such as `human-writing-ja` is available, use it
- Avoid technical identifiers in public-facing prose unless a command, file path, API name, error name, or GitHub keyword must be exact

If a rule conflicts with a user request, stop and explain the conflict before acting.

## Workflow

Read `references/issue-workflow.md` before starting implementation or PR work.
Read `assets/pr-body-template.md` before creating or editing a PR body.

Keep existing Issue operations read-only. PR body updates are the preferred way to link an Issue and report work.

## Push And PR Policy

Default: after SDD → implementation → verification → independent review → fixes are all green, run `git push -u origin <branch>` → `gh pr create --draft` without waiting for confirmation, from a feature branch in a dedicated worktree.

Some repositories require an explicit push instruction per turn. When the repository's rule file says so, stop at the commit and report.

Pushing to protected branches (`main` / `master` / `release/*`), adding `--force` / `--no-verify`, and pushing to a ready (non-draft) PR always require an explicit instruction.

## PR Link Policy

Use `Refs #番号` in the PR body regardless of who created the Issue.
Use an auto-closing keyword only when the user explicitly requests automatic closure of that exact Issue in the current conversation.

Before claiming a PR is linked, verify one of these.

- PR body contains `Refs #番号` or the explicitly requested auto-closing form
- GitHub Issue timeline shows a cross-reference from the PR
- GitHub UI or API shows the PR under the Issue development linkage

## Writing Policy

Use the current facts from commands and GitHub API output.
Avoid filler, praise, and AI-like wording.

For PR bodies, prefer short Japanese headings and concrete verification commands.
Do not include internal deliberation, memory citations, or implementation diary text.
Explain user-visible behavior first.
Keep exact commands and file paths in the verification section.
Do not expose implementation identifiers in the summary, cause, or fix sections when a plain Japanese phrase works.

## References

- `references/issue-workflow.md`: start, create (single call, only when no Issue exists), triage, implementation, commit, PR, final checks, completion report
- `assets/pr-body-template.md`: PR body skeleton
- `references/examples.md`: anonymized examples of triage, PR bodies, and the mutation gate in practice
