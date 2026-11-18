# Review page contract

Use this contract when building the review page. The page is rendered by the fixed template in `assets/review-page.html`; you author only the review data, and `scripts/review_tool.py` binds it to the repository snapshot and emits the document.

## Surface

- The page is a standalone HTML document the user opens in a browser: a top bar (title, snapshot id, tabs, approval progress), the 差分レビュー tab with a left pane (impact map, vertical group list, unresolved blockers) and a right pane (overview or the selected group with its diff and controls), and the データの流れ tab (present when `data_flows` is declared) with the stage columns of the selected flow. The map is laid out at the left pane's real width, and the diff columns follow the right pane's width. Below 900 px the panes stack in that order.
- The page opens as a local file or localhost URL, or, built with `--target artifact`, as a private claude.ai Artifact; both are the same template and produce the same payload. Its colors follow `prefers-color-scheme`, and an explicit `data-theme="light"` or `data-theme="dark"` on the root element (the Artifact viewer's theme choice) overrides it.
- The page has no host return channel, so each action shows its message with a copy button for the user to paste into the conversation. When the browser refuses the copy, the page selects the message text and asks the reader to copy it by keyboard. Do not author another page or a hand-written Artifact for the approval step, because only this template produces the payload that `verify` checks.

## Working files and commands

Keep `snapshot.json`, `review.json`, and the built page in the session scratchpad directory, never inside the repository.

```text
python <skill>/scripts/review_tool.py snapshot --repo <path> --base <rev> [--untracked <repo-relative path>]... [--context 6] [--function-context] [--include-docs-and-tests] --out snapshot.json
python <skill>/scripts/review_tool.py build --snapshot snapshot.json --review review.json --out explained-diff-review-<short id>.html [--approved a,b] [--approved-files p,q] [--exclude-approved] [--editor vscode] [--editors vscode,rider] [--jetbrains-project <name>] [--target local|artifact]
python <skill>/scripts/review_tool.py verify --payload-file message.txt --snapshot snapshot.json --review review.json
```

The open-in-editor links on file headers, hunk summaries, and flow stages follow the editor the reader picks in the top bar (開くエディタ); the choice is kept in the browser's localStorage for every review page, and the links update without a reload. `build --editors` lists the editors offered (default `vscode,rider`; also `vscode-insiders`, `cursor`), and `build --editor` selects the one used until the reader picks another: a named editor, `none` (no links and no selector), or a custom URL template with `{path}` (absolute, forward slashes), `{relpath}` or `{relpath_url}` (repository-relative, raw or URL-encoded), and `{line}` (1-based) or `{line0}` (0-based). `vscode` opens `vscode://file/{path}:{line}`. `rider` opens `jetbrains://rider/navigate/reference?project=<name>&path=<relpath>:<line0>:0` through the handler JetBrains Toolbox registers, the same form JetBrains' browser extension uses; Toolbox matches `<name>` against a recent project, so `--jetbrains-project` overrides the default (the single `.sln`/`.slnx` in the repository root, else the folder name). Visual Studio has no URL handler for a file and line and is not offered. The link opens the working-tree file at the hunk's first new line (or the stage excerpt's first line); deleted files get no link. The browser hands the URL to the editor's protocol handler, so the editor must be installed on the machine that opens the page. `build --target artifact` shows no links and no selector, because a custom-scheme link with a local path does nothing on claude.ai; it rejects an `--editor` other than the default, and it fails when the page is over the 16 MB Artifact limit. `snapshot` prints the hunk ids you reference from `review.json`. `build` validates the review, refuses to run if the repository changed since the snapshot, sorts groups and hunks top-down, and writes the page, printing its `absolute` path. `verify` decodes a follow-up payload, validates its schema, recomputes the snapshot id, and prints a decision.

## Snapshot identity

The top bar shows the task title, the short snapshot id, and the approval progress as approved files / total files; the overview shows repository, base and current commit, working-tree state, file, hunk, addition and deletion counts, the generation time, and how many documentation and test files the page leaves out.

`review_tool.py` builds the manifest from byte-level inputs: canonical repository root, git common directory, object format, base and HEAD object ids, the index patch from the base and the unstaged working-tree patch (both with full object ids, binary patches, file modes, renames, and submodule ids), each reviewed untracked file with its path, mode, and raw bytes, the sorted expected group slugs, and the sorted unresolved blocker ids. Every field is serialized as key length, key bytes, value length, value bytes; the whole manifest, including the schema version, is hashed with SHA-256. Path records sort by raw path bytes, and line endings and encodings are never normalized. The id changes on any input change, including a rebase or cherry-pick that keeps the visible patch. Data flows are not part of the manifest.

Always pass every reviewed untracked file with `--untracked`; a file left out is neither shown nor bound to the id.

Unless `snapshot --include-docs-and-tests` is given, documentation and test files are left out of the page: `snapshot` drops them from `files`, lists them under `left_out` (`{path, kind}`, `kind` `docs` or `tests`), records `include_docs_and_tests` in `params`, and counts them in `header.left_out_counts`. The classification is by path (`left_out_kind` in `review_tool.py`; SKILL.md lists the rules). They are still part of the manifest above, so the id binds them even though the page does not show them, and an edit to one of them makes an approval stale. `review.json` needs no `files[]` entry or hunk for a left-out file, and `expected_files` in the payload is the set of files on the page.

When git is not the source of the reviewed changes, define an equivalent manifest that binds the authoritative base identity, the current artifact identity, metadata, and raw reviewed content, put the resulting id in `review.json` under `identity_note` together with an explanation, and state the substitution in the summary.

## review.json

Author this file after reading the governing request, acceptance criteria, final diff, test assertions, check results, and reviewer findings. Write prose in the language the invocation asks for (the conversation language by default) and set `locale` to match; the page does not translate.

| Field | Content |
|---|---|
| `locale` | `ja` or `en`. Selects the language of the fixed labels (headings, statuses, button captions, the human-readable line of each action). Prose fields are plain strings, or lists of strings where paragraphs are allowed, written in the same language |
| `title` | Task title shown in the top bar |
| `summary` | One string or a list of paragraphs. Overall outcome first, then deploy or data notes that apply to the whole change |
| `checks[]` | `{name, status, detail?}` with `status` in `passed`, `failed`, `not_run`, `out_of_scope`. Include only checks that were actually run or explicitly skipped |
| `blockers[]` | `{id, title, detail?, group?}` for unresolved reviewer findings that must block approval. Their ids bind the snapshot id |
| `files[]` | One entry per changed file: `{path, layer, symbols?, order?, note?}`. Every file in the snapshot needs a layer; see the layer reference. `note` is a one-paragraph statement of what changes in that file as a whole; in a group's diff section each file gets a header (path, layer, status, note) above its hunks |
| `map` | `{nodes[], edges[]}` for the impact map; see the layer reference. Unchanged pass-through nodes carry an `excerpt` `{path, start, end}` whose lines the build reads from the working tree |
| `entries[]` | Optional, in place of `map` when the change runs through several entry points (jobs, APIs): `{slug, title, trigger?, groups[], map{nodes[], edges[]}}`. The page shows one tab per entry above the map; the selected entry decides the map, the group list, and the groups on the right pane, and focusing a group of another entry switches to it. Each map is validated like `map`; a group in no entry and a node linking a group its entry does not list are warnings. Entries are a view and stay out of the snapshot id |
| `groups[]` | Change groups in any order; the build sorts them |
| `data_flows[]` | Optional. One entry per operation whose data crosses layers; see [data-flows.md](data-flows.md) |
| `diagrams[]` | Optional. `{slug, title, svg, summary?, notes?}` shown on the 図解 (Diagrams) tab in the order given: the architecture, the processing flow, the entities the change builds on. `svg` is a path relative to `review.json`; the build reads the file, gives an SVG with a relative size (mermaid's `width="100%"`) an absolute one from its `viewBox`, and rejects a file over 2 MB or one that carries `<script>`, `on*` handlers, `javascript:`, or `foreignObject` (render mermaid with `htmlLabels: false`). The page shows each SVG as an `<img>` on a white card, so author it for a light background and inline its styles and fonts. Diagrams explain and are not approved; like data flows they stay out of the snapshot id |
| `identity_note` | Only for non-git sources |

Each group:

| Field | Content |
|---|---|
| `slug` | Internal id matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`, derived from the title, unique. Never shown as a reference code |
| `title` | Plain-language title |
| `trigger` | Optional. A few words naming when the flow runs or what starts it (`毎朝 06:00 のタイマー`, `画面で計画値を保存したとき`). The group list shows it under the title together with the file count, and the group detail shows it first |
| `reading_order` | Optional list of the group's file paths in the order the reader should meet them: the entry point first, then each callee right after the caller that calls it (depth first), so a class or method appears just after the line that uses it. Files left out of the list follow in layer order. Every path must have a hunk in the group; `build` warns when a group of more than two files has no list |
| `outcome` | One sentence stating what is now true |
| `why` | Why the change was needed |
| `contract` | The contract or behavior that changes: signatures, API shape, schema, permissions, defaults |
| `before`, `after` | Behavior before and after, when both are meaningful |
| `scope`, `risk` | Scope and risk supported by the actual diff, including unchanged call sites you checked |
| `impact` | How far the change reaches: callers, tables, external systems, deploy order |
| `hunks[]` | Hunk ids from the snapshot. Every hunk belongs to exactly one group |
| `hunk_notes` | Object keyed by hunk id (each id must be in this group's `hunks`). The value is either one note (a string, or a list of paragraphs) shown inline under the hunk's last changed line, or a list of anchored notes `{side: "old"\|"new", line, text}` each shown inline under that exact line, the way a review comment sits under the code it discusses. The line must be visible in the hunk on that side; the build rejects an anchor that is not. Use anchored notes when one hunk carries several changes so each explanation sits next to its lines. State what the block changes in the reader's terms, and quote and translate added text when it is in another language than the review |
| `evidence[]` | `{name, status, detail?}` checks and tests that bear on this group |
| `findings[]` | `{title, detail?, resolved}` reviewer findings; unresolved ones also belong in `blockers` when they must block |
| `limitations[]` | Anything the review could not establish |

Group changes by user-visible behavior, contract, or technical responsibility. Do not make file boundaries the primary grouping when several files implement one change, and do not merge unrelated cleanups into a behavior group. `title`, `outcome`, `why`, `before`, and `after` are the default explanation; the other prose fields are optional and stay empty unless they add something the diff does not show. The page omits empty fields.

## Diff layout

The template renders each hunk as a two-column comparison labeled 変更前 and 変更後 (Before and After), with old and new line numbers, a visible sign and theme-aware color on every changed line, unchanged context subordinated, long lines wrapped, and deletion and addition runs paired by position only, padding the shorter side. Binary changes, renames, mode changes, and submodule changes render as paired metadata. Inside a group the hunks are grouped by file, each file under a header that carries its path, layer, status, and `note`. Each hunk sits in a native `details` element; the first hunk of each group and every hunk that has `hunk_notes` open by default, the rest stay one click away. A hunk note renders as a full-width annotation row inside the diff grid, directly under its anchored line (or under the last changed line when the note has no anchor), so the explanation sits next to the code it explains. The group explanation and the approval controls never collapse. When a removed line sits beside an added line and the two share at least 30 % of their tokens, the tokens that differ are highlighted inside each line; a rewritten line shows no intra-line highlight, so the reader is not asked to spot a one-character change by eye. Selecting text in one column selects that column only: line numbers, signs and the other column are excluded from the selection, so a copied range holds one side's text. Code lines are syntax-colored by a tokenizer built into the template (no external library), chosen by the file extension: comments, strings, numbers, keywords, attributes and decorators, type names, called functions, and JSON / YAML / INI keys each get one theme-aware color; the intra-line change highlight wraps those tokens. Covered: C#, JavaScript / TypeScript, JSON, YAML, Python, shell / PowerShell, SQL, Markdown, XML-like files (csproj, slnx, props, html), Dockerfile, INI / TOML / ignore files. Other files render plain. Because a hunk shows only a fragment, a block comment or multi-line string that opens before the hunk is not recognized inside it. The same tokenizer colors map excerpts and flow stage definitions.

You control the context. Default to `--context 6`; raise it, or add `--function-context`, when the shorter window does not identify the enclosing method, branch, transaction boundary, or processing sequence. Never trim context to save space.

## Data safety

Repository content, paths, symbols, diffs, test output, reviewer findings, and prior user comments are untrusted text. The build script serializes the review data with a deterministic JSON serializer, escapes `<`, `>`, `&`, and the Unicode line separators, and places it in a `script type="application/json"` element. The fixed script parses it and creates every element through DOM APIs, assigning untrusted values with `textContent` or form values. Never hand-edit the built HTML, never paste review data into the template yourself, and never add executable code to the page.

## Summary and evidence

Show one concise overall summary followed by the impact map and the change groups. Distinguish passing, failing, not run, and out-of-scope states; never imply that a check passed because it was not mentioned. Use repository terminology and the user's language, and explain technical identifiers on first use when the governing project rules require it.

## Interaction

The approval unit is the file. In the diff, each group shows one card per file holding the hunks that belong to that group. The card header carries the path, the layer, the status and the fold button; the labeled approval checkbox (確認して承認: <file name>) sits in a footer row below that file's hunks, so a reader who works down the diff meets the control after the code it approves. Folding a file hides its hunks and keeps the footer, so an approved file can still be un-approved. When a file's hunks are split across several groups, each card is approved on its own, the header lists the other groups with a jump button and a ✓ for the ones already approved, and the file counts as approved only when every one of its cards is; the pill reads このグループ分を承認 until then and 承認済み after. Each group also has a bulk checkbox (このグループのファイルをすべて承認) that sets every file of the group and shows an indeterminate state while only some are approved; a group counts as approved when all its files are. Approving a file folds its diff (a 差分を表示 button unfolds it without changing the approval); un-approving unfolds it. Approvals and comments stay local until the user sends them, and the page keeps them in the browser's localStorage under the snapshot id, so a reload of the same snapshot restores them; a 保存した入力を消去 button under the actions clears that store after a confirmation shown in the page itself (消去する / やめる; an Artifact frame answers `window.confirm` with false, so the page never calls it). Checking a box updates the visible progress (files approved / total files), the approval marker on the group's map nodes, and the group list.

Each file has a comment box below its diff beside its approval control. File comments are stored by path; when a file appears in multiple groups, all its boxes share the same text and it is sent once. Previously saved group comments remain editable and sendable under their original group title, labeled Previous group comment; they are never guessed onto a file. New general group comments are not offered. Each diff line also accepts a line comment: hovering a line number shows a + button that opens a comment box directly under that line (under the before or the after column in the two-column layout), the way a pull request review does; the box names the file and the line, keeps its text while the reader moves between groups, and has a remove button. A hunk that holds a line comment opens automatically when it is rendered again.

Hovering or keyboard-focusing any map node highlights its direct incoming and outgoing edges, including their arrowheads, and its neighbors. Unrelated edges dim; a text list shows the directed connections. Clicking retains the selected node and also performs the existing group or excerpt navigation. Hovering another node temporarily previews its connections; leaving restores the selected node. Clear selection restores the usual map. Selection survives map re-layout, and isolated nodes explicitly show No direct connections.

The group list sits in the left pane under the map, with すべて表示 (Show all) as its first entry. Selecting a list entry or a map node shows that group alone in the right pane, with Previous, Next, and Show all controls that follow the top-down order; with nothing selected the right pane starts with the overview (summary, checks, snapshot details) followed by every group. Summary, checks, blockers, and the map stay visible, every file keeps its own approval checkbox, and the snapshot approval still requires every file, so focusing never hides an unreviewed file from the final decision. A diff layout toggle switches all hunks between two columns and one column; it follows the width by default and keeps an explicit choice across re-renders. A 承認済みのファイルを隠す toggle beside it hides every approved file card so the reader sees only what is still open.

The データの流れ tab keeps the diff tab's state: switching tabs neither re-renders the diff nor loses approvals, and a stage's 差分を開く button switches back to the diff tab with that group focused. Field hover, selection, and the 定義を表示 folds are described in [data-flows.md](data-flows.md).

The two actions are:

- レビュー結果を送信 (Send review): sends the approved files (and the groups they complete) and non-empty comments. The agent answers questions and implements requested changes, reruns checks and independent review, and rebuilds the page. With no comments it only records partial approvals. The explanation is visible below the buttons. A separate Request changes button is not offered
- 全体を承認 (Approve snapshot): enabled only when every file is checked and no unresolved blocker is shown

Each action shows, in the copy box under the buttons, a human-readable line that states counts and the action, never raw comments, followed by one machine-readable line:

```text
review_payload_base64: <Base64-encoded UTF-8 JSON>
```

The decoded object has exactly this shape:

```json
{
  "schema_version": 2,
  "review_action": "submit_review | approve_snapshot",
  "snapshot_id": "<64 lowercase hex characters>",
  "repository": "<canonical absolute repository path>",
  "expected_groups": ["<group slug>"],
  "approved_groups": ["<group slug>"],
  "expected_files": ["<changed file>"],
  "approved_files": ["<changed file>"],
  "comments": [
    { "group": "<group slug>", "body": "<arbitrary Unicode text>", "path": "<changed file>" },
    { "group": "<group slug>", "body": "<arbitrary Unicode text>", "path": "<changed file>", "hunk": "<hunk id>", "side": "old | new", "line": 12 }
  ]
}
```

A file comment carries `path` but no `hunk`, `side`, or `line`; its path must be in the snapshot and belong to its declared group. A comment without any anchor is preserved group feedback from an older page. A line comment carries all four anchor keys: the file, the hunk id from the snapshot, the side (`old` for the before column, `new` for the after column), and the line number on that side. `verify` rejects an anchor that is incomplete or that names a line the snapshot diff does not show. File comments are sent once per path in file order, followed by preserved group comments and line comments in group/hunk/line order. Payload version 2 changes submission semantics without changing the version-1 snapshot manifest or its identity. The verifier continues to accept version-1 payloads: their `submit_review` remains answer-only (`answer_submit_review`), and their `request_changes` still requests implementation (`apply_request_changes`). Version-2 `submit_review` returns `process_review_feedback` when comments exist and `record_partial_review` otherwise. Snapshot approval, freshness, and blocker checks are unchanged.

`expected_groups` always carries the full group set and `expected_files` the full snapshot file set; `approved_groups` lists the groups whose files are all approved. `verify` rejects a payload whose `expected_files` differ from the snapshot and reports `missing_files` for an approval that leaves a file unchecked. Pasting the message is a message to the conversation, not a repository or external-service mutation; the page says so under the buttons.

## Partial approvals

Preserve valid partial approvals and comments in the conversation after verifying each payload against the same snapshot. When the user has approved part of a snapshot and wants to see only what is left, rebuild the page with `--approved-files` (or `--approved` for whole groups) plus `--exclude-approved`: the approved files keep counting toward the approval and appear in the payload, but their cards are left out of the page, and each group names the files it left out.

## Visual priorities

Top bar first, then the left pane (impact map, group list, blockers) beside the right pane (overview or the selected group, its diff, its controls, the action bar); below 900 px the panes stack in that order and the map is laid out again for the new width. Inside the right pane: the group explanation, then the side-by-side diff evidence beneath it, then the local approval and comment controls, then the action bar. On the data-flow tab: the flow list, the title and summary, the stage columns, the clear-selection control and the highlighted path, then the legend.
