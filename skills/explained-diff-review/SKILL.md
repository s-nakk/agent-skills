---
name: explained-diff-review
description: Create an interactive explained diff review page after code or tracked-document changes, so the user can inspect grouped changes ordered from the UI down to storage, see an impact map of the edited files and their connections, follow the data model of each operation stage by stage (table, entity, read model or command, API contract, generated client type, screen), comment, and approve an exact snapshot before the workflow continues. Use whenever the user asks for an explained review screen, a review page, a "説明付きレビュー", a "レビュー画面", a "データの流れ", or has established it as the review step after implementation, even if they only say "review this before we move on". Do not use for read-only reviews of someone else's code or for work with no changes.
---

# Explained Diff Review

Present completed changes as a reviewable page, not as a prose-only handoff. This review complements tests and any independent review required by the repository; it does not replace them.

This skill is shared by Claude Code and Codex from one directory. The review data, the build tool, and the page template are identical on both hosts; the page opens in the user's browser on either.

## Required tooling

- Python 3 and git on PATH for `scripts/review_tool.py`, which captures the deterministic snapshot, extracts the contextual diff, validates and orders the review data, builds the page, and verifies follow-up payloads.
- The fixed page template `assets/review-page.html`. Never author page HTML or JavaScript by hand; the template is the only executable code the page contains, and it styles itself with theme-aware defaults for light and dark mode.

Read [references/review-screen-contract.md](references/review-screen-contract.md) for the data schema, commands, and interaction contract, [references/layer-order-and-impact-map.md](references/layer-order-and-impact-map.md) for layer assignment, ordering, and the impact map, and [references/data-flows.md](references/data-flows.md) for the data-flow tab before authoring the review data.

## The page

`build` writes one standalone HTML document: a top bar with the title, the snapshot id, the tabs, and the approval progress; under the 差分レビュー (Diff review) tab a left pane with the impact map, the group list, and unresolved blockers, and a right pane with the overview or the selected group and its diff; under the データの流れ (Data flow) tab, present when the review declares flows, one column per stage of an operation with field-level lines between the stages. The page is always the whole review.

Write it to the scratchpad or the task's working directory as `explained-diff-review-<short snapshot id>.html`, never into the repository, and give the user the `absolute` path from the build output so they can open it in their browser. Use a host preview only when it runs the page's script: the Claude Code desktop browser pane shows a `file://` page from outside the project as a static snapshot, so serve the directory over localhost (for example `python -m http.server <port> --bind 127.0.0.1` in that directory, stopped when the review is done) or leave the file to the user's browser.

The page has no return channel. Each action shows the message it would have sent, including the `review_payload_base64:` line, with a copy button; the user pastes it into the conversation.

## Workflow

1. Finish the implementation and the checks required for the current snapshot. If repository rules require an independent review, complete it before presenting this page.
2. Capture the snapshot into the session scratchpad or the task's working directory, never inside the repository. Pass every reviewed untracked file explicitly. The base is the merge-base with the repository's main branch (the whole change set of the branch or PR) unless the user names another revision; a head the user already reviewed is never a default base, because a page that shows only the latest fix-up commits hides what the change does against main.

   ```text
   python <skill>/scripts/review_tool.py snapshot --repo <repo> --base <base rev> --untracked <path> --out <scratch>/snapshot.json
   ```

   The output lists the hunk ids. Default context is 6 lines; add `--function-context` or a larger `--context` when the enclosing method or processing sequence is not identifiable from the shorter window. If the repository marks generated files `-diff` in `.gitattributes`, git renders them as binary; a local `.git/info/attributes` line such as `path/** diff` restores their text diff for the snapshot (the snapshot id is computed from git's diff output, so keep the line until the approval is verified).
3. Read the governing request, acceptance criteria, final diff, test assertions, check results, and reviewer findings. Do not rely on the implementation summary as evidence.
4. Author `<scratch>/review.json`:
   - Assign every changed file a layer from the generic taxonomy (UI, client data access, API boundary, application, domain, persistence, infrastructure, configuration, tests, docs, other). The build sorts groups, files, and hunks from the entry point toward storage so the reader follows the call chain top-down.
   - Group changes by processing flow, and keep the groups few: one group per flow the change touches, from its trigger to its sink (a daily batch, a request, a queue message, an import); one group for a cleanup that several flows share; one group for documentation and generated artifacts. Inside a group the reader goes top-down along that flow. Do not split a flow into one group per behavior or per file: a dozen small groups hide which flow each change belongs to. Every hunk belongs to exactly one group. The default explanation of a group is short: `outcome`, `why`, `before`, `after`, each one or two sentences. Fill `contract`, `scope`, `risk`, `impact`, `findings`, and `limitations` only when they carry something the reader cannot see in the diff (a deploy order, an accepted gap, an unresolved finding); a reviewer reads many groups, and prose that restates the diff costs more attention than it saves. Take every statement from the reviewed artifacts only.
   - Explain each block, not only each group. A group explanation tells the reader why the change exists; it does not tell them what one diff block does, and a reader who has to infer that from the raw lines loses the benefit of the explanation. Give every hunk a `hunk_notes` entry when a group spans several hunks, and use anchored notes (`{side, line, text}`) when one hunk carries more than one change, so each explanation renders under the lines it explains rather than as one paragraph for the whole block. Give a file a `note` when its role in the change is not obvious from its path; it becomes the header above that file's hunks. Write a note as three labeled lines, `変更前:` / `変更後:` / `理由:` (`Before:` / `After:` / `Why:` in English), each a full sentence that stands on its own: what the old text said in its context (translated when it is in another language than the review, so the reader judges the text and not a paraphrase), what the new text says, and why the change was made. A fragment such as "dropped AB#1234" makes the reader reconstruct the context from the raw lines; the labels render in the page as a small table.
   - Describe the impact map: changed files or symbols plus every unchanged hop between them on the way from the entry point to the sink, with edges in call or data-flow direction. The path must be continuous so a reader can follow it top-down; give unchanged pass-through nodes an `excerpt` (file and line range) so their code opens from the map. Stay within 16 nodes and 24 edges; fold the rest into one node per layer.
   - Describe the data flows when the change carries data across layers (a list or detail read, a create, an update, an import): one flow per operation, its stages in the order the data moves (table, entity, read model or command, API contract, generated client type, screen type, screen), the fields of each stage read from its definition with an `excerpt`, and a mapping per field to the field it becomes in the next stage, with the mapper expression or rule in the note. The tab then shows where each value is copied, renamed, converted, computed, born, or dropped. A read flow and a write flow are separate flows; when the change is a read path, a write flow of the same entity marked `unchanged` shows the reviewer where the rows come from. See the data-flow reference for the shape and the authoring rules.
   - Add diagrams when the reviewer needs a picture the diff cannot give: the architecture the change sits in, the processing flow (trigger, queue, handler, what is written), the entities and their links. Write each as a standalone SVG file (entities as a mermaid `erDiagram` rendered with `mmdc` and `htmlLabels: false`) and list it under `diagrams`; the page shows them on a separate 図解 (Diagrams) tab. The file rules are in the contract.
   - Record checks with their real state (passed, failed, not run, out of scope) and unresolved blockers.
   - Decide the language from the invocation. No language mentioned: write the prose in the conversation language and set `locale` to match. "英語で" or "in English": write English prose with `locale: "en"`. `locale` selects the language of the page's fixed labels; the page does not translate prose, so write it once and consistently. Paths, symbols, and other language-neutral strings stay as they are.
5. Build the page and hand the user its path or its localhost URL.

   ```text
   python <skill>/scripts/review_tool.py build --snapshot <scratch>/snapshot.json --review <scratch>/review.json --out <scratch>/explained-diff-review-<short id>.html
   ```

   Fix every validation error the build reports and read its warnings (a map edge that skips a layer, a flow whose stages move against its direction). The build refuses to run when the repository changed since the snapshot.
6. Return the page in the same turn. Keep the surrounding response to a single short sentence unless a blocker or risk must be stated outside the page.

## Follow-up handling

When the user pastes a comment or approval from the page, the message ends with a `review_payload_base64:` line. Save the message text to the scratchpad and run:

```text
python <skill>/scripts/review_tool.py verify --payload-file <scratch>/message.txt --snapshot <scratch>/snapshot.json --review <scratch>/review.json
```

The verifier rejects malformed payloads, unsupported versions, mismatched repositories, duplicate or unknown groups, and values outside the action enum, then recomputes the snapshot id from the repository, the expected group set, and the unresolved blockers in `review.json`. Act on its `decision`:

- `reject`: explain the validation errors and regenerate the page if the user still wants to review.
- `stale`: the snapshot changed. Do not apply the old approval. Explain that the review is stale, capture a new snapshot, and generate a replacement page.
- `apply_request_changes`: revise the reviewed work within the current task scope, rerun the applicable checks and independent review, capture a new snapshot, and generate a fresh page with a new snapshot id.
- File comments carry `path` without a line anchor. Apply or answer them for that file; comments without a path are preserved group feedback from older pages and must not be guessed onto one file.
- Comments may carry a line anchor (`path`, `hunk`, `side`, `line`) from the diff. Treat an anchored comment as feedback on that exact line: quote the file and line when you answer it, and make the revision there when you apply it.
- `process_review_feedback`: answer questions and implement actionable change requests in the comments within the authorized task scope. Then rerun the applicable checks and independent review, capture a new snapshot when files changed, and regenerate the page. Do not infer final approval from a submission; preserve approvals only for files whose reviewed diff did not change. Comments that are questions alone need an answer, not a speculative edit. Clarify only genuinely ambiguous or out-of-scope requests.
- `record_partial_review`: no comments were submitted. Record the partial approval state without modifying files or treating it as final approval; rebuild the same snapshot with the verified approvals when needed.
- `answer_submit_review`: a submission from an older, version-1 page; partial review state only. Do not modify files, approve the snapshot, or continue the workflow. Answer the submitted comments, keep the partial approvals in the conversation, and regenerate the same snapshot page with `--approved-files` (or `--approved` for whole groups) when another user decision is needed, and add `--exclude-approved` so the approved files leave the page and the reader sees only what is still open. Do the same when a snapshot goes stale after a partial approval: carry the approvals of the files whose diff did not change into the new build, and leave any file whose diff changed unapproved.
- `reject_approval`: approved files or groups miss part of the expected set, or blockers remain. Say which files, groups, or blockers are outstanding and regenerate the page.
- `accept_approval`: treat it as acceptance of that exact snapshot and permission to continue only with steps already authorized by the task and the governing repository workflow.

Never interpret review approval as authorization to push, create or mutate a pull request, merge, deploy, change production, or perform another separately gated action. Preserve comments in the conversation and reflect resolved comments in the next page. Do not invent a durable approval record unless the user asks for one.

Update the unresolved blockers in `review.json` before verifying when a blocker was resolved after the page was shown; the snapshot id binds them, so an outdated blocker list reports the approval as stale. Data flows do not enter the id, so a flow added or corrected after the page was shown keeps the approval valid.
