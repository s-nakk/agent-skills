---
name: explained-diff-review
description: Create an interactive explained diff review screen after code or tracked-document changes, so the user can inspect grouped changes ordered from the UI down to storage, see an impact map of the edited files and their connections, comment, and approve an exact snapshot before the workflow continues. Use whenever the user asks for an explained review screen, a review widget, a "説明付きレビュー", a "レビュー画面", or has established it as the review step after implementation, even if they only say "review this before we move on". Do not use for read-only reviews of someone else's code or for work with no changes.
---

# Explained Diff Review

Present completed changes as a reviewable conversation surface, not as a prose-only handoff. This review complements tests and any independent review required by the repository; it does not replace them.

This skill is shared by Claude Code and Codex from one directory. The review data, the build tool, and the widget template are identical on both hosts; only the way the widget is shown and the way its actions return to the conversation differ. Both hosts can also emit the same review as a standalone two-pane page when the inline width is not enough. See the host section below.

## Required tooling

- Python 3 and git on PATH for `scripts/review_tool.py`, which captures the deterministic snapshot, extracts the contextual diff, validates and orders the review data, builds the widget, and verifies follow-up payloads.
- The fixed widget template `assets/review-widget.html`, and the document wrapper `assets/review-page.html` that `--layout page` puts around the same fragment. Never author widget HTML or JavaScript by hand; the template is the only executable code the screen contains. It styles itself from the host's theme tokens on both hosts and falls back to theme-aware defaults elsewhere.
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

Standalone page (both hosts):

- Add `--layout page` to the build when the user asks for a separate HTML file or a wider or two-pane view, or when the inline width is too narrow for the diff or the map (long lines, many nodes, many groups). The build wraps the same fragment in `assets/review-page.html`, a complete document: a top bar with the title and the progress; a left pane with the impact map, the group list, and unresolved blockers; a right pane with the overview or the selected group and its diff. The page is always the whole review; split fragments are refused.
- Write it to the scratchpad or the task's working directory as `explained-diff-review-<short snapshot id>.html`, never into the repository, and give the user the `absolute` path from the build output so they can open it in their browser. Use a host preview only when it runs the page's script: the Claude Code desktop browser pane shows a `file://` page from outside the project as a static snapshot, so serve the directory over localhost or leave the file to the user's browser.
- The page has no return channel. Each action shows the message it would have sent, including the `review_payload_base64:` line, with a copy button; the user pastes it into the conversation. Verify and act on it exactly like a widget message.

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
   - Group changes by user-visible behavior, contract, or technical responsibility, not by file. Every hunk belongs to exactly one group. The default explanation of a group is short: `outcome`, `why`, `before`, `after`, each one or two sentences. Fill `contract`, `scope`, `risk`, `impact`, `findings`, and `limitations` only when they carry something the reader cannot see in the diff (a deploy order, an accepted gap, an unresolved finding); a reviewer reads many groups, and prose that restates the diff costs more attention than it saves. Take every statement from the reviewed artifacts only.
   - Explain each block, not only each group. A group explanation tells the reader why the change exists; it does not tell them what one diff block does, and a reader who has to infer that from the raw lines loses the benefit of the explanation. Give every hunk a `hunk_notes` entry when a group spans several hunks, and use anchored notes (`{side, line, text}`) when one hunk carries more than one change, so each explanation renders under the lines it explains rather than as one paragraph for the whole block. Give a file a `note` when its role in the change is not obvious from its path; it becomes the header above that file's hunks. Write a note as three labeled lines, `変更前:` / `変更後:` / `理由:` (`Before:` / `After:` / `Why:` in English), each a full sentence that stands on its own: what the old text said in its context (translated when it is in another language than the review, so the reader judges the text and not a paraphrase), what the new text says, and why the change was made. A fragment such as "dropped AB#1234" makes the reader reconstruct the context from the raw lines; the labels render in the screen as a small table.
   - Describe the impact map: changed files or symbols plus every unchanged hop between them on the way from the entry point to the sink, with edges in call or data-flow direction. The path must be continuous so a reader can follow it top-down; give unchanged pass-through nodes an `excerpt` (file and line range) so their code opens from the map. Stay within 16 nodes and 24 edges; fold the rest into one node per layer.
   - Record checks with their real state (passed, failed, not run, out of scope) and unresolved blockers.
   - Decide the language from the invocation. No language mentioned: write the prose in the conversation language and set `locale` to match. "英語で" or "in English": write English prose with `locale: "en"`. `locale` selects the language of the screen's fixed labels; the screen does not translate prose, so write it once and consistently. Paths, symbols, and other language-neutral strings stay as they are.
5. Build and show the screen.

   ```text
   python <skill>/scripts/review_tool.py build --snapshot <scratch>/snapshot.json --review <scratch>/review.json --out <output path>
   ```

   Fix every validation error the build reports, then show the widget the way the host section describes. Add `--layout page` for the standalone page described there when the inline width is not enough.
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
- Comments may carry a line anchor (`path`, `hunk`, `side`, `line`) from the diff. Treat an anchored comment as feedback on that exact line: quote the file and line when you answer it, and make the revision there when you apply it.
- `answer_submit_review`: partial review state only. Do not modify files, approve the snapshot, or continue the workflow. Answer the submitted comments, keep the partial approvals in the conversation, and regenerate the same snapshot screen with `--approved-files` (or `--approved` for whole groups) when another user decision is needed.
- `reject_approval`: approved files or groups miss part of the expected set, or blockers remain. Say which files, groups, or blockers are outstanding and regenerate the screen.
- `accept_approval`: treat it as acceptance of that exact snapshot and permission to continue only with steps already authorized by the task and the governing repository workflow.

Never interpret review approval as authorization to push, create or mutate a pull request, merge, deploy, change production, or perform another separately gated action. Preserve comments in the conversation and reflect resolved comments in the next screen. Do not invent a durable approval record unless the user asks for one.

Update the unresolved blockers in `review.json` before verifying when a blocker was resolved after the screen was shown; the snapshot id binds them, so an outdated blocker list reports the approval as stale.
