---
name: explained-diff-review
description: Create an interactive explained diff review screen after code or tracked-document changes, so the user can inspect grouped changes ordered from the UI down to storage, see an impact map of the edited files and their connections, comment, and approve an exact snapshot before the workflow continues. Use whenever the user asks for an explained review screen, a review widget, a "説明付きレビュー", a "レビュー画面", or has established it as the review step after implementation, even if they only say "review this before we move on". Do not use for read-only reviews of someone else's code or for work with no changes.
---

# Explained Diff Review

Present completed changes as a reviewable conversation surface, not as a prose-only handoff. This review complements tests and any independent review required by the repository; it does not replace them.

This skill is shared by Claude Code and Codex from one directory. The review data, the build tool, and the widget template are identical on both hosts; only the way the widget is shown and the way its actions return to the conversation differ. See the host section below.

## Required tooling

- Python 3 and git on PATH for `scripts/review_tool.py`, which captures the deterministic snapshot, extracts the contextual diff, validates and orders the review data, builds the widget, and verifies follow-up payloads.
- The fixed widget template `assets/review-widget.html`. Never author widget HTML or JavaScript by hand; the template is the only executable code the screen contains. It styles itself from the host's theme tokens on both hosts and falls back to theme-aware defaults elsewhere.
- The host's inline visualization surface, described in the host section.

Read [references/review-screen-contract.md](references/review-screen-contract.md) for the data schema, commands, and interaction contract, and [references/layer-order-and-impact-map.md](references/layer-order-and-impact-map.md) for layer assignment, ordering, and the impact map before authoring the review data.

## Host surfaces

Claude Code:

- The `visualize` MCP server provides `read_me` and `show_widget`. Call `read_me` once per session with `modules: ["interactive"]` because the host requires it before the first `show_widget`; the template already follows its rules, so do not restyle the widget from that guidance.
- Read the built `widget.html` and pass its full content as `widget_code` to `show_widget`, with a title such as `explained_diff_review_<short snapshot id>` and plain loading messages.
- Actions return through the widget's `sendPrompt` global as a new user message.

Codex:

- Load the bundled `visualize` skill first, as it requires, and follow its file, fragment, and response rules. The built `widget.html` is already a fragment with a unique root id, no document markup, and no external resources.
- Build the widget directly into the thread-scoped visualization directory (or the task's `work/` directory when no thread directory is writable) with `--out <that directory>/explained-diff-review-<short snapshot id>.html`, then put the content reference on its own line in the final response where the screen should appear, using the absolute path. Use `"mode":"wide"` for full and group fragments because the side-by-side diff needs the width; index and final fragments stay at normal width.

  ```text
  visualize{"path":"<absolute-path>/explained-diff-review-<short snapshot id>.html","mode":"wide"}
  ```

- Actions return through `window.openai.sendFollowUpMessage` as a follow-up message. The template prefers this API when present and otherwise uses `sendPrompt`.

## Workflow

1. Finish the implementation and the checks required for the current snapshot. If repository rules require an independent review, complete it before presenting this screen.
2. Capture the snapshot into the session scratchpad or the task's working directory, never inside the repository. Pass every reviewed untracked file explicitly.

   ```text
   python <skill>/scripts/review_tool.py snapshot --repo <repo> --base <base rev> --untracked <path> --out <scratch>/snapshot.json
   ```

   The output lists the hunk ids. Default context is 6 lines; add `--function-context` or a larger `--context` when the enclosing method or processing sequence is not identifiable from the shorter window.
3. Read the governing request, acceptance criteria, final diff, test assertions, check results, and reviewer findings. Do not rely on the implementation summary as evidence.
4. Author `<scratch>/review.json`:
   - Assign every changed file a layer from the generic taxonomy (UI, client data access, API boundary, application, domain, persistence, infrastructure, configuration, tests, docs, other). The build sorts groups, files, and hunks from the entry point toward storage so the reader follows the call chain top-down.
   - Group changes by user-visible behavior, contract, or technical responsibility, not by file. Every hunk belongs to exactly one group. Fill why, contract, before and after behavior, scope, risk, impact, evidence, findings, and limitations from the reviewed artifacts only.
   - Describe the impact map: changed files or symbols plus every unchanged hop between them on the way from the entry point to the sink, with edges in call or data-flow direction. The path must be continuous so a reader can follow it top-down; give unchanged pass-through nodes an `excerpt` (file and line range) so their code opens from the map. Stay within 16 nodes and 24 edges; fold the rest into one node per layer.
   - Record checks with their real state (passed, failed, not run, out of scope) and unresolved blockers.
   - Decide the languages from the invocation, not from the audience you imagine. No language mentioned: write plain strings in the conversation language and set `locale` accordingly. "英語で" or "in English": write plain English strings with `locale: "en"`. "日英で" or "bilingual": set `languages` to `["ja", "en"]` and write every prose field as `{"ja": "...", "en": "..."}`; the build then rejects any Japanese-only string so nothing stays untranslated when a reader switches. Paths, symbols, and other language-neutral strings may stay plain. Readers can switch the fixed labels at any time, and a single-language screen offers a button that asks you for the other language later, so do not write two languages up front unless asked.
5. Build and show the screen.

   ```text
   python <skill>/scripts/review_tool.py build --snapshot <scratch>/snapshot.json --review <scratch>/review.json --out <output path>
   ```

   Fix every validation error the build reports, then show the widget the way the host section describes.
6. Return the screen in the same turn. Keep the surrounding response to a single short sentence unless a blocker or risk must be stated outside the screen.

If the widget would be too large to stream comfortably, use the split-review flow in the contract reference: an index fragment, group fragments, and a final confirmation fragment that alone offers 全体を承認. Never offer final approval from fragments that cannot see the full review state.

## Follow-up handling

When the user sends a comment or approval from the screen, the message ends with a `review_payload_base64:` line. Save the message text to the scratchpad and run:

```text
python <skill>/scripts/review_tool.py verify --payload-file <scratch>/message.txt --snapshot <scratch>/snapshot.json --review <scratch>/review.json
```

The verifier rejects malformed payloads, unsupported versions, mismatched repositories, duplicate or unknown groups, and values outside the action enum, then recomputes the snapshot id from the repository, the expected group set, and the unresolved blockers in `review.json`. Act on its `decision`:

- `reject`: explain the validation errors and regenerate the screen if the user still wants to review.
- `stale`: the snapshot changed. Do not apply the old approval. Explain that the review is stale, capture a new snapshot, and generate a replacement screen.
- `apply_request_changes`: revise the reviewed work within the current task scope, rerun the applicable checks and independent review, capture a new snapshot, and generate a fresh screen with a new snapshot id.
- `answer_submit_review`: partial review state only. Do not modify files, approve the snapshot, or continue the workflow. Answer the submitted comments, keep the partial approvals in the conversation, and regenerate the same snapshot screen with `--approved` when another user decision is needed.
  - When the human-readable line carries `add_language: <ja|en>`, the user pressed the translation button. Add that language to every prose field of `review.json`, set `languages` to both, rebuild with `--approved` listing the verified `approved_groups`, keep the submitted comments in the conversation, and show the new screen. The snapshot id does not change because prose is not part of the manifest.
- `reject_approval`: approved groups miss part of the expected set, or blockers remain. Say which groups or blockers are outstanding and regenerate the screen.
- `accept_approval`: treat it as acceptance of that exact snapshot and permission to continue only with steps already authorized by the task and the governing repository workflow.

Never interpret review approval as authorization to push, create or mutate a pull request, merge, deploy, change production, or perform another separately gated action. Preserve comments in the conversation and reflect resolved comments in the next screen. Do not invent a durable approval record unless the user asks for one.

Update the unresolved blockers in `review.json` before verifying when a blocker was resolved after the screen was shown; the snapshot id binds them, so an outdated blocker list reports the approval as stale.
