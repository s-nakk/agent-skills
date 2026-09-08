# Review screen contract

Use this contract when building the review screen, inline or as a standalone page. The screen is rendered by the fixed template in `assets/review-widget.html`; you author only the review data, and `scripts/review_tool.py` binds it to the repository snapshot and emits the widget HTML, optionally wrapped in `assets/review-page.html`.

## Surface

- The screen is an inline HTML widget rendered by the host's visualization surface. On Claude Code that is the `show_widget` tool of the `visualize` MCP server, which receives the built HTML as `widget_code` and exposes a `sendPrompt(text)` global. On Codex that is the bundled `visualize` skill, which renders the built HTML file referenced by a `visualize{"path":...}` line and exposes `window.openai.sendFollowUpMessage({ prompt, title })`. The template detects which return channel exists, so the same file works on both hosts.
- Claude Code requires one `read_me` call before the first `show_widget` call in a session; call it with `modules: ["interactive"]`. Codex requires loading its `visualize` skill first. The template already follows both hosts' design rules, so do not restyle the widget from that guidance.
- The widget fills the host width: 680 px on Claude Code, 736 px or 1,024 px in wide mode on Codex. The template keeps the before and after columns side by side above 560 px and stacks each hunk (before first, after second) below that.
- `build --layout page` emits the same review as a standalone document (`assets/review-page.html` around the fragment) for when the inline width is not enough: a top bar, a left pane with the impact map, a vertical group list, and unresolved blockers, and a right pane with the overview or the selected group. The map is laid out at the left pane's real width, and the diff columns follow the right pane's width. The page has no host return channel, so each action shows its message with a copy button for the user to paste into the conversation; the payload is identical. Do not use an Artifact or any other page for the approval step, because only these two surfaces produce the payload that `verify` checks.

## Working files and commands

Keep `snapshot.json`, `review.json`, and `widget.html` in the session scratchpad directory, never inside the repository.

```text
python <skill>/scripts/review_tool.py snapshot --repo <path> --base <rev> [--untracked <repo-relative path>]... [--context 6] [--function-context] --out snapshot.json
python <skill>/scripts/review_tool.py build --snapshot snapshot.json --review review.json --out widget.html [--layout widget|page] [--fragment full|index|group|final] [--groups a,b] [--index n --total m] [--approved a,b] [--approved-files p,q]
python <skill>/scripts/review_tool.py verify --payload-file message.txt --snapshot snapshot.json --review review.json
```

`build --editor` selects the open-in-editor links on file headers and hunk summaries: `vscode` (default, `vscode://file/{path}:{line}`), `vscode-insiders`, `cursor`, `none`, or a custom URL template with `{path}` (absolute, forward slashes) and `{line}`. The link opens the working-tree file at the hunk's first new line; deleted files get no link. The browser hands the URL to the editor's protocol handler, so the editor must be installed on the machine that opens the page. `snapshot` prints the hunk ids you reference from `review.json`. `build` validates the review, refuses to run if the repository changed since the snapshot, sorts groups and hunks top-down, and writes the widget; with `--layout page` it writes the standalone document instead and prints its `absolute` path, and it refuses any `--fragment` other than `full`. `verify` decodes a follow-up payload, validates its schema, recomputes the snapshot id, and prints a decision.

## Snapshot identity

The header shows repository, task title, base and current commit, working-tree state, file, hunk, addition and deletion counts, the short snapshot id, the generation time, and the approval progress as approved files / total files.

`review_tool.py` builds the manifest from byte-level inputs: canonical repository root, git common directory, object format, base and HEAD object ids, the index patch from the base and the unstaged working-tree patch (both with full object ids, binary patches, file modes, renames, and submodule ids), each reviewed untracked file with its path, mode, and raw bytes, the sorted expected group slugs, and the sorted unresolved blocker ids. Every field is serialized as key length, key bytes, value length, value bytes; the whole manifest, including the schema version, is hashed with SHA-256. Path records sort by raw path bytes, and line endings and encodings are never normalized. The id changes on any input change, including a rebase or cherry-pick that keeps the visible patch.

Always pass every reviewed untracked file with `--untracked`; a file left out is neither shown nor bound to the id.

When git is not the source of the reviewed changes, define an equivalent manifest that binds the authoritative base identity, the current artifact identity, metadata, and raw reviewed content, put the resulting id in `review.json` under `identity_note` together with an explanation, and state the substitution in the summary.

## review.json

Author this file after reading the governing request, acceptance criteria, final diff, test assertions, check results, and reviewer findings. Write prose in the language the invocation asks for (the conversation language by default) and set `locale` to match; the screen does not translate.

| Field | Content |
|---|---|
| `locale` | `ja` or `en`. Selects the language of the fixed labels (headings, statuses, button captions, the human-readable line of each action). Prose fields are plain strings, or lists of strings where paragraphs are allowed, written in the same language |
| `title` | Task title shown in the header |
| `summary` | One string or a list of paragraphs. Overall outcome first, then deploy or data notes that apply to the whole change |
| `checks[]` | `{name, status, detail?}` with `status` in `passed`, `failed`, `not_run`, `out_of_scope`. Include only checks that were actually run or explicitly skipped |
| `blockers[]` | `{id, title, detail?, group?}` for unresolved reviewer findings that must block approval. Their ids bind the snapshot id |
| `files[]` | One entry per changed file: `{path, layer, symbols?, order?, note?}`. Every file in the snapshot needs a layer; see the layer reference. `note` is a one-paragraph statement of what changes in that file as a whole; in a group's diff section each file gets a header (path, layer, status, note) above its hunks, and the index and final fragments show the note in the file list instead |
| `map` | `{nodes[], edges[]}` for the impact map; see the layer reference. Unchanged pass-through nodes carry an `excerpt` `{path, start, end}` whose lines the build reads from the working tree |
| `groups[]` | Change groups in any order; the build sorts them |
| `identity_note` | Only for non-git sources |

Each group:

| Field | Content |
|---|---|
| `slug` | Internal id matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`, derived from the title, unique. Never shown as a reference code |
| `title` | Plain-language title |
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

Group changes by user-visible behavior, contract, or technical responsibility. Do not make file boundaries the primary grouping when several files implement one change, and do not merge unrelated cleanups into a behavior group. `title`, `outcome`, `why`, `before`, and `after` are the default explanation; the other prose fields are optional and stay empty unless they add something the diff does not show. The screen omits empty fields.

## Diff layout

The template renders each hunk as a two-column comparison labeled 変更前 and 変更後 (Before and After), with old and new line numbers, a visible sign and theme-aware color on every changed line, unchanged context subordinated, long lines wrapped, and deletion and addition runs paired by position only, padding the shorter side. Binary changes, renames, mode changes, and submodule changes render as paired metadata. Inside a group the hunks are grouped by file, each file under a header that carries its path, layer, status, and `note`. Each hunk sits in a native `details` element; the first hunk of each group and every hunk that has `hunk_notes` open by default, the rest stay one click away. A hunk note renders as a full-width annotation row inside the diff grid, directly under its anchored line (or under the last changed line when the note has no anchor), so the explanation sits next to the code it explains. The group explanation and the approval controls never collapse. When a removed line sits beside an added line and the two share at least 30 % of their tokens, the tokens that differ are highlighted inside each line; a rewritten line shows no intra-line highlight, so the reader is not asked to spot a one-character change by eye. Selecting text in one column selects that column only: line numbers, signs and the other column are excluded from the selection, so a copied range holds one side's text.

You control the context. Default to `--context 6`; raise it, or add `--function-context`, when the shorter window does not identify the enclosing method, branch, transaction boundary, or processing sequence. Never trim context to save space; split the review instead.

## Data safety

Repository content, paths, symbols, diffs, test output, reviewer findings, and prior user comments are untrusted text. The build script serializes the review data with a deterministic JSON serializer, escapes `<`, `>`, `&`, and the Unicode line separators, and places it in a `script type="application/json"` element. The fixed script parses it and creates every element through DOM APIs, assigning untrusted values with `textContent` or form values. Never hand-edit the built HTML, never paste review data into the template yourself, and never add executable code to the widget.

## Summary and evidence

Show one concise overall summary followed by the impact map and the change groups. Distinguish passing, failing, not run, and out-of-scope states; never imply that a check passed because it was not mentioned. Use repository terminology and the user's language, and explain technical identifiers on first use when the governing project rules require it.

## Interaction

The approval unit is the file. In the diff, each group shows one card per file holding the hunks that belong to that group, and the card header carries a labeled checkbox (確認して承認: <file name>). When a file's hunks are split across several groups, each card is approved on its own, the header lists the other groups with a jump button and a ✓ for the ones already approved, and the file counts as approved only when every one of its cards is; the pill reads このグループ分を承認 until then and 承認済み after. Each group also has a bulk checkbox (このグループのファイルをすべて承認) that sets every file of the group and shows an indeterminate state while only some are approved; a group counts as approved when all its files are. Approving a file folds its diff (a 差分を表示 button unfolds it without changing the approval); un-approving unfolds it. Approvals and comments stay local until the user sends them, and the screen keeps them in the browser's localStorage under the snapshot id, so a reload of the same snapshot restores them; a 保存した入力を消去 button under the actions clears that store after a confirmation. Checking a box updates the visible progress (files approved / total files), the approval marker on the group's map nodes, and the group strip.

Comments come in two forms. Each group has a general comment box under its diff. Each diff line also accepts a line comment: hovering a line number shows a + button that opens a comment box directly under that line (under the before or the after column in the two-column layout), the way a pull request review does; the box names the file and the line, keeps its text while the reader moves between groups, and has a remove button. A hunk that holds a line comment opens automatically when it is rendered again.

The screen offers a focus mode. Selecting a map node or a group in the strip shows that group alone below the map, with Previous, Next, and Show all controls; Previous and Next follow the top-down order. Summary, checks, blockers, and the map stay visible, every file keeps its own approval checkbox, and the snapshot approval still requires every file, so focusing never hides an unreviewed file from the final decision. A diff layout toggle switches all hunks between two columns and one column; it follows the width by default and keeps an explicit choice across re-renders.

On the standalone page the group list sits in the left pane under the map, with すべて表示 (Show all) as its first entry, and selecting a list entry or a map node replaces the right pane. With nothing selected the right pane starts with the overview (summary, checks, snapshot details) followed by every group.

The three actions are:

- レビュー結果を送信 (Send review): sends the approved files (and the groups they complete) and non-empty comments
- 修正を依頼 (Request changes): sends the current non-empty comments without approving; the widget refuses to send without a comment and shows an accessible message
- 全体を承認 (Approve snapshot): enabled only when every file is checked and no unresolved blocker is shown

Each action delivers, through the host return channel or the page's copy box, a human-readable line that states counts and the action, never raw comments, followed by one machine-readable line:

```text
review_payload_base64: <Base64-encoded UTF-8 JSON>
```

The decoded object has exactly this shape:

```json
{
  "schema_version": 1,
  "review_action": "request_changes | submit_review | approve_snapshot",
  "snapshot_id": "<64 lowercase hex characters>",
  "repository": "<canonical absolute repository path>",
  "expected_groups": ["<group slug>"],
  "approved_groups": ["<group slug>"],
  "expected_files": ["<changed file>"],
  "approved_files": ["<changed file>"],
  "comments": [
    { "group": "<group slug>", "body": "<arbitrary Unicode text>" },
    { "group": "<group slug>", "body": "<arbitrary Unicode text>", "path": "<changed file>", "hunk": "<hunk id>", "side": "old | new", "line": 12 }
  ]
}
```

A comment without an anchor is the group's general comment. A line comment carries all four anchor keys: the file, the hunk id from the snapshot, the side (`old` for the before column, `new` for the after column), and the line number on that side. `verify` rejects an anchor that is incomplete or that names a line the snapshot diff does not show. Comments are ordered by group, then by hunk, then by line.

`expected_groups` always carries the full group set and `expected_files` the full snapshot file set, also in split-review fragments; `approved_groups` lists the groups whose files are all approved. `verify` rejects a payload whose `expected_files` differ from the snapshot and reports `missing_files` for an approval that leaves a file unchecked. Sending is a message to the conversation, not a repository or external-service mutation; the widget says so under the buttons.

## Split reviews

When one screen would be too large, build an `index` fragment (overview, map, group list, no diffs, no actions), one `group` fragment per group or set of groups with `--groups`, `--index`, and `--total`, and finally a `final` fragment (group and file lists with recorded approvals via `--approved` or `--approved-files`, no diffs) that alone offers 全体を承認. All fragments share one snapshot and snapshot id. Group fragments offer only sending and requesting changes.

Preserve valid partial approvals and comments in the conversation after verifying each payload against the same snapshot. Once every file is reviewed and blockers are resolved, build the final fragment with `--approved-files` (or `--approved` for whole groups) listing the verified approvals.

## Visual priorities

Overview first, then the impact map, then the group strip and layout controls, then grouped explanations in top-down layer order (all groups, or the focused one) with side-by-side diff evidence beneath each explanation, then local approval and comment controls, then the action bar. Keep the page readable at 680 px, and stack controls and each diff's before and after columns on narrow screens.

On the standalone page: the top bar, then the left pane (impact map, group list, blockers) beside the right pane (overview or the selected group, its diff, its controls, the action bar); below 900 px the panes stack in that order and the map is laid out again for the new width.
