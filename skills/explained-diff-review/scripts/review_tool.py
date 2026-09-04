#!/usr/bin/env python3
"""Support tool for the explained-diff-review skill.

Subcommands:
  snapshot  Capture the deterministic review manifest and the contextual diff of a git repository.
  build     Validate the authored review JSON, bind it to the snapshot, and emit the widget HTML
            (an inline fragment by default, or a standalone two-pane page with --layout page).
  verify    Validate a follow-up payload against the current repository state.

Standard library only. Requires git on PATH.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from datetime import datetime
from html import escape as html_escape
from pathlib import Path

SCHEMA_VERSION = 1
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
ACTIONS = ("request_changes", "submit_review", "approve_snapshot")
CHECK_STATUSES = ("passed", "failed", "not_run", "out_of_scope")
NODE_STATUSES = ("modified", "added", "deleted", "renamed", "unchanged")
FRAGMENT_KINDS = ("full", "index", "group", "final")
LAYOUTS = ("widget", "page")
MAP_NODE_BUDGET = 16
MAP_EDGE_BUDGET = 24
EXCERPT_MAX_LINES = 120
# Layer ranks are spaced by 10; a downward edge spanning more than this usually skips a pass-through layer.
LAYER_SKIP_WARN = 20
NON_CODE_RANK = 70
PLACEHOLDER = "__REVIEW_DATA_JSON__"
PAGE_TITLE_PLACEHOLDER = "__REVIEW_TITLE__"
PAGE_LANG_PLACEHOLDER = "__REVIEW_LANG__"
PAGE_BODY_PLACEHOLDER = "__REVIEW_WIDGET_HTML__"

# key, rank, Japanese label, English label. Rank orders layers from the entry point toward storage.
LAYERS = [
    ("presentation", 10, "画面", "UI"),
    ("client_data", 15, "画面のデータ取得", "Client data access"),
    ("api", 20, "API 境界", "API boundary"),
    ("application", 30, "アプリケーション", "Application"),
    ("domain", 40, "ドメイン", "Domain"),
    ("persistence", 50, "永続化", "Persistence"),
    ("infrastructure", 60, "基盤・外部連携", "Infrastructure"),
    ("config", 70, "設定・ビルド", "Configuration and build"),
    ("tests", 80, "テスト", "Tests"),
    ("docs", 90, "ドキュメント", "Documentation"),
    ("other", 100, "その他", "Other"),
]
LAYER_INDEX = {key: (rank, ja, en) for key, rank, ja, en in LAYERS}


class ToolError(Exception):
    pass


def fail(message: str) -> None:
    raise ToolError(message)


# ---------------------------------------------------------------------------
# git helpers


def run_git(repo: str, args: list[str], check: bool = True) -> bytes:
    proc = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if check and proc.returncode != 0:
        fail("git " + " ".join(args) + " failed: " + proc.stderr.decode("utf-8", "replace").strip())
    return proc.stdout


def git_text(repo: str, args: list[str]) -> str:
    return run_git(repo, args).decode("utf-8", "replace").strip()


def canonical_root(repo: str) -> str:
    return git_text(repo, ["rev-parse", "--show-toplevel"])


def unquote_c(path: str) -> str:
    if not (len(path) >= 2 and path[0] == '"' and path[-1] == '"'):
        return path
    body = path[1:-1]
    out = bytearray()
    i = 0
    while i < len(body):
        ch = body[i]
        if ch != "\\":
            out += ch.encode("utf-8")
            i += 1
            continue
        i += 1
        esc = body[i]
        simple = {"n": 10, "t": 9, "r": 13, "\\": 92, '"': 34, "a": 7, "b": 8, "f": 12, "v": 11}
        if esc in simple:
            out.append(simple[esc])
            i += 1
        elif esc.isdigit():
            out.append(int(body[i : i + 3], 8))
            i += 3
        else:
            out += esc.encode("utf-8")
            i += 1
    return out.decode("utf-8", "replace")


def strip_prefix(path: str, prefix: str) -> str:
    path = unquote_c(path)
    return path[len(prefix) :] if path.startswith(prefix) else path


def working_tree_summary(repo: str, reviewed_untracked: list[str]) -> str:
    raw = run_git(repo, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    entries = raw.split(b"\0")
    staged = unstaged = untracked = 0
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 3:
            continue
        x, y = chr(entry[0]), chr(entry[1])
        if x == "?" and y == "?":
            untracked += 1
            continue
        if x in "RC":
            i += 1
        if x != " ":
            staged += 1
        if y != " ":
            unstaged += 1
    parts = [f"staged {staged}", f"unstaged {unstaged}", f"untracked {untracked}"]
    if reviewed_untracked:
        parts.append(f"reviewed untracked {len(reviewed_untracked)}")
    if staged == 0 and unstaged == 0 and untracked == 0:
        return "clean"
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# manifest


def manifest_digest(repo: str, base: str, untracked: list[str], groups: list[str], blockers: list[str]) -> tuple[str, dict]:
    """Hash the byte-level manifest that identifies the reviewed snapshot.

    Every field is serialized as (key length, key bytes, value length, value bytes) so that
    the digest changes whenever any input changes, including rebases that keep the visible patch.
    """
    root = canonical_root(repo)
    common_dir = git_text(repo, ["rev-parse", "--path-format=absolute", "--git-common-dir"])
    object_format = git_text(repo, ["rev-parse", "--show-object-format"])
    base_oid = git_text(repo, ["rev-parse", "--verify", f"{base}^{{commit}}"])
    head_oid = git_text(repo, ["rev-parse", "--verify", "HEAD^{commit}"])
    common = ["-c", "core.quotepath=off", "diff", "--full-index", "--binary", "--find-renames", "--no-color", "--no-ext-diff", "--no-textconv", "--submodule=short"]
    index_patch = run_git(repo, [*common, "--cached", base_oid, "--"])
    worktree_patch = run_git(repo, [*common, "--"])
    fields: list[tuple[str, bytes]] = [
        ("schema_version", str(SCHEMA_VERSION).encode()),
        ("repository_root", root.encode("utf-8")),
        ("git_common_dir", common_dir.encode("utf-8")),
        ("object_format", object_format.encode()),
        ("base_oid", base_oid.encode()),
        ("head_oid", head_oid.encode()),
        ("index_patch", index_patch),
        ("worktree_patch", worktree_patch),
    ]
    records = []
    for rel in untracked:
        full = Path(root) / rel
        if not full.is_file():
            fail(f"untracked path is not a file: {rel}")
        mode = "100755" if os.name != "nt" and full.stat().st_mode & stat.S_IXUSR else "100644"
        records.append((rel.encode("utf-8"), mode.encode(), full.read_bytes()))
    records.sort(key=lambda r: r[0])
    for path_bytes, mode_bytes, content in records:
        fields.append(("untracked_path", path_bytes))
        fields.append(("untracked_mode", mode_bytes))
        fields.append(("untracked_bytes", content))
    fields.append(("expected_groups", "\n".join(sorted(groups)).encode("utf-8")))
    fields.append(("blockers", "\n".join(sorted(blockers)).encode("utf-8")))
    blob = bytearray()
    for key, value in fields:
        kb = key.encode("utf-8")
        blob += len(kb).to_bytes(4, "big") + kb + len(value).to_bytes(8, "big") + value
    digest = hashlib.sha256(bytes(blob)).hexdigest()
    header = {
        "repository": root,
        "git_common_dir": common_dir,
        "object_format": object_format,
        "base_ref": base,
        "base_oid": base_oid,
        "head_oid": head_oid,
    }
    return digest, header


# ---------------------------------------------------------------------------
# diff parsing

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)$")


def split_diff_git_line(line: str) -> tuple[str, str]:
    body = line[len("diff --git ") :]
    if body.startswith('"'):
        m = re.match(r'^("(?:[^"\\]|\\.)*") ("(?:[^"\\]|\\.)*")$', body)
        if m:
            return strip_prefix(m.group(1), "a/"), strip_prefix(m.group(2), "b/")
    if body.startswith("a/"):
        rest = body[2:]
        n = (len(rest) - 3) // 2
        if rest == rest[:n] + " b/" + rest[:n]:
            return rest[:n], rest[:n]
        idx = rest.find(" b/")
        if idx >= 0:
            return rest[:idx], rest[idx + 3 :]
    return body, body


def parse_unified_diff(text: str) -> list[dict]:
    lines = text.split("\n")
    files: list[dict] = []
    cur: dict | None = None
    hunk: dict | None = None
    old_left = new_left = 0
    for line in lines:
        if hunk is not None and (old_left > 0 or new_left > 0):
            if line.startswith("\\"):
                hunk["rows"].append(["\\", None, None, line[1:].strip()])
                continue
            tag = line[:1] if line else " "
            body = line[1:] if line else ""
            if tag == " ":
                hunk["rows"].append([" ", hunk["_old"], hunk["_new"], body])
                hunk["_old"] += 1
                hunk["_new"] += 1
                old_left -= 1
                new_left -= 1
            elif tag == "-":
                hunk["rows"].append(["-", hunk["_old"], None, body])
                hunk["_old"] += 1
                old_left -= 1
            elif tag == "+":
                hunk["rows"].append(["+", None, hunk["_new"], body])
                hunk["_new"] += 1
                new_left -= 1
            else:
                fail(f"unexpected line inside hunk: {line[:80]}")
            continue
        if line.startswith("\\") and hunk is not None:
            hunk["rows"].append(["\\", None, None, line[1:].strip()])
            continue
        if line.startswith("diff --git "):
            old_p, new_p = split_diff_git_line(line)
            cur = {"path": new_p, "old_path": old_p, "status": "modified", "binary": False, "old_mode": None, "new_mode": None, "submodule": None, "hunks": []}
            files.append(cur)
            hunk = None
            continue
        if cur is None:
            continue
        if line.startswith("old mode "):
            cur["old_mode"] = line[9:].strip()
        elif line.startswith("new mode "):
            cur["new_mode"] = line[9:].strip()
        elif line.startswith("deleted file mode "):
            cur["status"] = "deleted"
            cur["old_mode"] = line[18:].strip()
        elif line.startswith("new file mode "):
            cur["status"] = "added"
            cur["new_mode"] = line[14:].strip()
        elif line.startswith("rename from "):
            cur["status"] = "renamed"
            cur["old_path"] = unquote_c(line[12:])
        elif line.startswith("rename to "):
            cur["path"] = unquote_c(line[10:])
        elif line.startswith("Binary files "):
            cur["binary"] = True
        elif line.startswith("--- "):
            p = line[4:]
            cur["old_path"] = None if p == "/dev/null" else strip_prefix(p, "a/")
        elif line.startswith("+++ "):
            p = line[4:]
            if p != "/dev/null":
                cur["path"] = strip_prefix(p, "b/")
        elif line.startswith("@@ "):
            m = HUNK_RE.match(line)
            if not m:
                fail(f"unparseable hunk header: {line}")
            old_start, old_count = int(m.group(1)), int(m.group(2) or 1)
            new_start, new_count = int(m.group(3)), int(m.group(4) or 1)
            hunk = {"old_start": old_start, "old_count": old_count, "new_start": new_start, "new_count": new_count, "header": m.group(5).strip(), "rows": [], "_old": old_start, "_new": new_start}
            cur["hunks"].append(hunk)
            old_left, new_left = old_count, new_count
    for f in files:
        if f["status"] == "deleted":
            f["path"] = f["old_path"] or f["path"]
        elif f["old_path"] is None and f["status"] == "modified":
            f["status"] = "added"
        elif f["status"] == "modified" and f["old_mode"] and f["new_mode"] and not f["hunks"]:
            f["status"] = "mode"
        for hk in f["hunks"]:
            hk.pop("_old", None)
            hk.pop("_new", None)
            sub_old = [r[3] for r in hk["rows"] if r[0] == "-" and r[3].startswith("Subproject commit ")]
            sub_new = [r[3] for r in hk["rows"] if r[0] == "+" and r[3].startswith("Subproject commit ")]
            if sub_old or sub_new:
                f["submodule"] = {"old": sub_old[0][len("Subproject commit ") :] if sub_old else None, "new": sub_new[0][len("Subproject commit ") :] if sub_new else None}
                f["status"] = "submodule"
                hk["rows"] = []
        if f["binary"] and f["status"] == "modified":
            f["status"] = "binary"
        if not f["hunks"]:
            f["hunks"].append({"old_start": None, "old_count": 0, "new_start": None, "new_count": 0, "header": "", "rows": []})
        for n, hk in enumerate(f["hunks"], 1):
            hk["id"] = f"{f['path']}#{n}"
    return files


def untracked_file_record(root: str, rel: str) -> dict:
    data = (Path(root) / rel).read_bytes()
    rec = {"path": rel, "old_path": None, "status": "added", "binary": False, "old_mode": None, "new_mode": "100644", "submodule": None, "hunks": []}
    if b"\0" in data[:8000]:
        rec["binary"] = True
        rec["hunks"].append({"id": f"{rel}#1", "old_start": None, "old_count": 0, "new_start": None, "new_count": 0, "header": "", "rows": []})
        return rec
    text = data.decode("utf-8", "replace")
    lines = text.split("\n")
    trailing_newline = text.endswith("\n")
    if trailing_newline:
        lines = lines[:-1]
    rows = [["+", None, i + 1, line] for i, line in enumerate(lines)]
    if lines and not trailing_newline:
        rows.append(["\\", None, None, "No newline at end of file"])
    rec["hunks"].append({"id": f"{rel}#1", "old_start": 0, "old_count": 0, "new_start": 1, "new_count": len(lines), "header": "", "rows": rows})
    return rec


def extract_display_diff(repo: str, base_oid: str, context: int, function_context: bool) -> list[dict]:
    args = ["-c", "core.quotepath=off", "-c", "diff.mnemonicPrefix=false", "-c", "diff.noprefix=false", "diff", "--find-renames", "--no-color", "--no-ext-diff", "--no-textconv", "--submodule=short", f"-U{context}"]
    if function_context:
        args.append("--function-context")
    args += [base_oid, "--"]
    raw = run_git(repo, args)
    return parse_unified_diff(raw.decode("utf-8", "replace"))


def count_changes(files: list[dict]) -> dict:
    additions = deletions = hunks = 0
    for f in files:
        for hk in f["hunks"]:
            if hk["old_start"] is not None or hk["rows"]:
                hunks += 1
            for r in hk["rows"]:
                if r[0] == "+":
                    additions += 1
                elif r[0] == "-":
                    deletions += 1
    return {"files": len(files), "hunks": hunks, "additions": additions, "deletions": deletions}


# ---------------------------------------------------------------------------
# snapshot subcommand


def cmd_snapshot(args: argparse.Namespace) -> int:
    repo = canonical_root(args.repo)
    untracked = sorted(set(args.untracked or []))
    core_digest, header = manifest_digest(repo, args.base, untracked, [], [])
    files = extract_display_diff(repo, header["base_oid"], args.context, args.function_context)
    tracked_paths = {f["path"] for f in files}
    for rel in untracked:
        if rel in tracked_paths:
            fail(f"path is tracked, not untracked: {rel}")
        files.append(untracked_file_record(repo, rel))
    files.sort(key=lambda f: f["path"])
    header["working_tree"] = working_tree_summary(repo, untracked)
    header["counts"] = count_changes(files)
    header["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "params": {"repo": repo, "base": args.base, "untracked": untracked, "context": args.context, "function_context": bool(args.function_context)},
        "core_digest": core_digest,
        "header": header,
        "files": files,
    }
    Path(args.out).write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = {"out": args.out, "repository": repo, "base": header["base_oid"][:10], "head": header["head_oid"][:10], "working_tree": header["working_tree"], "counts": header["counts"], "hunk_ids": [hk["id"] for f in files for hk in f["hunks"]]}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


# ---------------------------------------------------------------------------
# build subcommand


def load_json(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail(f"cannot read JSON {path}: {exc}")
        return {}


def check_text(value, where: str, errors: list[str], allow_list: bool = True) -> None:
    """Validate a prose field: a plain string, or (where allowed) a list of strings.

    Prose is written once, in the language selected by `locale`; the screen does not translate.
    """
    if value is None:
        return
    if isinstance(value, list):
        if not allow_list:
            errors.append(f"{where}: a list is not allowed here")
            return
        for i, item in enumerate(value):
            check_text(item, f"{where}[{i}]", errors, allow_list=False)
        return
    if not isinstance(value, str):
        errors.append(f"{where}: must be a string")


def validate_texts(review: dict, errors: list[str]) -> None:
    check_text(review.get("title"), "title", errors, allow_list=False)
    check_text(review.get("summary"), "summary", errors)
    check_text(review.get("identity_note"), "identity_note", errors, allow_list=False)
    for i, c in enumerate(review.get("checks", []) or []):
        check_text(c.get("name"), f"checks[{i}].name", errors, allow_list=False)
        check_text(c.get("detail"), f"checks[{i}].detail", errors, allow_list=False)
    for i, b in enumerate(review.get("blockers", []) or []):
        check_text(b.get("title"), f"blockers[{i}].title", errors, allow_list=False)
        check_text(b.get("detail"), f"blockers[{i}].detail", errors, allow_list=False)
    m = review.get("map") or {}
    for n in m.get("nodes", []) or []:
        check_text(n.get("label"), f"map.nodes[{n.get('id')}].label", errors, allow_list=False)
        check_text(n.get("note"), f"map.nodes[{n.get('id')}].note", errors, allow_list=False)
    for i, e in enumerate(m.get("edges", []) or []):
        check_text(e.get("kind"), f"map.edges[{i}].kind", errors, allow_list=False)
        check_text(e.get("label"), f"map.edges[{i}].label", errors, allow_list=False)
    for g in review.get("groups", []) or []:
        slug = g.get("slug")
        for key in ("title", "outcome", "why", "contract", "before", "after", "scope", "risk", "impact"):
            check_text(g.get(key), f"groups[{slug}].{key}", errors, allow_list=key != "title")
        for i, ev in enumerate(g.get("evidence", []) or []):
            check_text(ev.get("name"), f"groups[{slug}].evidence[{i}].name", errors, allow_list=False)
            check_text(ev.get("detail"), f"groups[{slug}].evidence[{i}].detail", errors, allow_list=False)
        for i, fd in enumerate(g.get("findings", []) or []):
            check_text(fd.get("title"), f"groups[{slug}].findings[{i}].title", errors, allow_list=False)
            check_text(fd.get("detail"), f"groups[{slug}].findings[{i}].detail", errors, allow_list=False)
        check_text(g.get("limitations"), f"groups[{slug}].limitations", errors)


def validate_review(review: dict, snapshot: dict, errors: list[str], warnings: list[str]) -> None:
    validate_texts(review, errors)
    locale = review.get("locale", "ja")
    if locale not in ("ja", "en"):
        errors.append(f"locale must be ja or en: {locale}")
    groups = review.get("groups")
    if not isinstance(groups, list) or not groups:
        errors.append("groups must be a non-empty list")
        return
    seen: set[str] = set()
    for g in groups:
        slug = g.get("slug")
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            errors.append(f"invalid group slug: {slug!r}")
            continue
        if slug in seen:
            errors.append(f"duplicate group slug: {slug}")
        seen.add(slug)
        if not g.get("title"):
            errors.append(f"group {slug} needs a title")
        if not g.get("outcome"):
            errors.append(f"group {slug} needs an outcome sentence")
        for ev in g.get("evidence", []) or []:
            if ev.get("status") not in CHECK_STATUSES:
                errors.append(f"group {slug} evidence status invalid: {ev.get('status')}")
    for c in review.get("checks", []) or []:
        if c.get("status") not in CHECK_STATUSES:
            errors.append(f"check status invalid: {c.get('status')}")
    for b in review.get("blockers", []) or []:
        if not b.get("id") or not b.get("title"):
            errors.append("each blocker needs id and title")
        if b.get("group") and b["group"] not in seen:
            errors.append(f"blocker refers to unknown group: {b.get('group')}")
    snapshot_paths = {f["path"] for f in snapshot["files"]}
    file_layers = {}
    for f in review.get("files", []) or []:
        p = f.get("path")
        if p not in snapshot_paths:
            errors.append(f"files entry does not match any changed file: {p}")
            continue
        if f.get("layer") not in LAYER_INDEX:
            errors.append(f"unknown layer for {p}: {f.get('layer')}")
        file_layers[p] = f
    for p in sorted(snapshot_paths - set(file_layers)):
        errors.append(f"changed file has no layer assignment in files: {p}")
    hunk_ids = {hk["id"] for f in snapshot["files"] for hk in f["hunks"]}
    assigned: dict[str, str] = {}
    for g in groups:
        slug = g.get("slug")
        for hid in g.get("hunks", []) or []:
            if hid not in hunk_ids:
                errors.append(f"group {slug} refers to unknown hunk id: {hid}")
            elif hid in assigned:
                errors.append(f"hunk {hid} is assigned to both {assigned[hid]} and {slug}")
            else:
                assigned[hid] = slug
    for hid in sorted(hunk_ids - set(assigned)):
        errors.append(f"hunk is not assigned to any group: {hid}")
    m = review.get("map") or {}
    nodes = m.get("nodes", []) or []
    edges = m.get("edges", []) or []
    node_ids: set[str] = set()
    for n in nodes:
        nid = n.get("id")
        if not nid or nid in node_ids:
            errors.append(f"map node id missing or duplicate: {nid!r}")
        node_ids.add(nid)
        if not n.get("label"):
            errors.append(f"map node {nid} needs a label")
        if n.get("layer") not in LAYER_INDEX:
            errors.append(f"map node {nid} has unknown layer: {n.get('layer')}")
        if n.get("status", "unchanged") not in NODE_STATUSES:
            errors.append(f"map node {nid} has invalid status: {n.get('status')}")
        if n.get("group") and n["group"] not in seen:
            errors.append(f"map node {nid} refers to unknown group: {n.get('group')}")
        note = n.get("note")
        if isinstance(note, str) and len(note) > 40:
            warnings.append(f"map node {nid} note is long; keep notes to a few words")
    for e in edges:
        if e.get("from") not in node_ids or e.get("to") not in node_ids:
            errors.append(f"map edge refers to unknown node: {e.get('from')} -> {e.get('to')}")
    repo_root = Path(snapshot["params"]["repo"])
    rank_of: dict[str, int] = {}
    for n in nodes:
        if n.get("layer") in LAYER_INDEX:
            rank_of[n.get("id")] = LAYER_INDEX[n["layer"]][0]
        ex = n.get("excerpt")
        if ex is None:
            continue
        if not isinstance(ex, dict) or not isinstance(ex.get("path"), str) or not isinstance(ex.get("start"), int) or not isinstance(ex.get("end"), int) or ex["start"] < 1 or ex["end"] < ex["start"]:
            errors.append(f"map node {n.get('id')} excerpt must be {{path, start, end}} with 1 <= start <= end")
            continue
        if not (repo_root / ex["path"]).is_file():
            errors.append(f"map node {n.get('id')} excerpt file not found in the working tree: {ex['path']}")
        elif ex["end"] - ex["start"] + 1 > EXCERPT_MAX_LINES:
            warnings.append(f"map node {n.get('id')} excerpt spans {ex['end'] - ex['start'] + 1} lines; keep excerpts within {EXCERPT_MAX_LINES}")
    touched = {e.get("from") for e in edges} | {e.get("to") for e in edges}
    for n in nodes:
        if n.get("status", "unchanged") != "unchanged" and n.get("id") not in touched:
            warnings.append(f"map node {n.get('id')} is changed but has no edge; connect it to its caller or callee so the path stays continuous")
    for e in edges:
        a, b = rank_of.get(e.get("from")), rank_of.get(e.get("to"))
        if a is None or b is None or a >= NON_CODE_RANK or b >= NON_CODE_RANK:
            continue
        if b - a > LAYER_SKIP_WARN:
            warnings.append(f"map edge {e.get('from')} -> {e.get('to')} skips intermediate layers; add the pass-through nodes with an excerpt, or confirm the direct call")
    if len(nodes) > MAP_NODE_BUDGET:
        warnings.append(f"map has {len(nodes)} nodes; keep the main path within {MAP_NODE_BUDGET} and summarize the rest")
    if len(edges) > MAP_EDGE_BUDGET:
        warnings.append(f"map has {len(edges)} edges; keep within {MAP_EDGE_BUDGET}")
    if nodes and not any(n.get("group") for n in nodes):
        warnings.append("no map node links to a group; changed nodes should carry the slug of the group that explains them")


def load_excerpt(repo_root: Path, ex: dict) -> dict:
    """Read an unchanged code excerpt from the working tree so pass-through nodes can show their code."""
    text = (repo_root / ex["path"]).read_bytes().decode("utf-8", "replace")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if ex["start"] > len(lines):
        fail(f"excerpt {ex['path']} starts at line {ex['start']} but the file has {len(lines)} lines")
    end = min(ex["end"], len(lines))
    rows = [[" ", i, i, lines[i - 1]] for i in range(ex["start"], end + 1)]
    return {"path": ex["path"], "start": ex["start"], "end": end, "rows": rows}


def compose_map(review: dict, snapshot: dict) -> dict:
    repo_root = Path(snapshot["params"]["repo"])
    map_in = review.get("map") or {}
    nodes_out = []
    for n in map_in.get("nodes", []) or []:
        node = dict(n)
        if n.get("excerpt"):
            node["excerpt"] = load_excerpt(repo_root, n["excerpt"])
        nodes_out.append(node)
    return {"nodes": nodes_out, "edges": map_in.get("edges", []) or []}


def compose_widget_data(review: dict, snapshot: dict, snapshot_id: str, fragment: dict, only_groups: list[str] | None, approved: list[str], layout: str) -> dict:
    locale = review.get("locale", "ja")
    header = snapshot["header"]
    file_info = {f["path"]: f for f in review.get("files", [])}
    snap_files = {f["path"]: f for f in snapshot["files"]}
    hunk_lookup: dict[str, tuple[dict, dict, int]] = {}
    for f in snapshot["files"]:
        for n, hk in enumerate(f["hunks"]):
            hunk_lookup[hk["id"]] = (f, hk, n)

    def file_rank(path: str) -> tuple:
        info = file_info[path]
        return (LAYER_INDEX[info["layer"]][0], info.get("order", 10**6), path)

    all_slugs = [g["slug"] for g in review["groups"]]
    groups_out = []
    for authored_index, g in enumerate(review["groups"]):
        hunk_refs = sorted(g.get("hunks", []) or [], key=lambda hid: (file_rank(hunk_lookup[hid][0]["path"]), hunk_lookup[hid][2]))
        hunks_out = []
        files_out = []
        seen_files: set[str] = set()
        min_rank = 10**9
        for hid in hunk_refs:
            f, hk, n = hunk_lookup[hid]
            info = file_info[f["path"]]
            rank = LAYER_INDEX[info["layer"]][0]
            min_rank = min(min_rank, rank)
            meta = {"status": f["status"]}
            if n == 0:
                meta.update({"old_path": f["old_path"], "old_mode": f["old_mode"], "new_mode": f["new_mode"], "binary": f["binary"], "submodule": f["submodule"]})
            if fragment["kind"] in ("full", "group"):
                hunks_out.append({"id": hid, "path": f["path"], "layer": info["layer"], "header": hk["header"], "old_start": hk["old_start"], "new_start": hk["new_start"], "rows": hk["rows"], "meta": meta})
            if f["path"] not in seen_files:
                seen_files.add(f["path"])
                files_out.append({"path": f["path"], "layer": info["layer"], "status": f["status"], "symbols": info.get("symbols", [])})
        entry = {
            "slug": g["slug"],
            "title": g["title"],
            "outcome": g.get("outcome"),
            "why": g.get("why"),
            "contract": g.get("contract"),
            "before": g.get("before"),
            "after": g.get("after"),
            "scope": g.get("scope"),
            "risk": g.get("risk"),
            "impact": g.get("impact"),
            "layer": next(k for k, r, _, _ in LAYERS if r == min_rank) if min_rank < 10**9 else None,
            "files": files_out,
            "hunks": hunks_out,
            "evidence": g.get("evidence", []) or [],
            "findings": g.get("findings", []) or [],
            "limitations": g.get("limitations", []) or [],
            "approved": g["slug"] in approved,
            "_rank": (min_rank, authored_index),
        }
        groups_out.append(entry)
    groups_out.sort(key=lambda e: e["_rank"])
    for e in groups_out:
        e.pop("_rank")
    if only_groups is not None:
        groups_out = [e for e in groups_out if e["slug"] in only_groups]
    present_layers = {info["layer"] for info in file_info.values()} | {n["layer"] for n in (review.get("map") or {}).get("nodes", []) or []}
    layers_out = [{"key": key, "rank": rank, "ja": ja, "en": en} for key, rank, ja, en in LAYERS if key in present_layers]
    return {
        "schema_version": SCHEMA_VERSION,
        "locale": locale,
        "layout": layout,
        "fragment": fragment,
        "snapshot": {
            "id": snapshot_id,
            "short_id": snapshot_id[:12],
            "repository": header["repository"],
            "task_title": review.get("title", ""),
            "base": {"ref": header["base_ref"], "oid": header["base_oid"], "short": header["base_oid"][:10]},
            "head": {"oid": header["head_oid"], "short": header["head_oid"][:10]},
            "working_tree": header["working_tree"],
            "counts": header["counts"],
            "generated_at": header["generated_at"],
            "identity_note": review.get("identity_note"),
        },
        "summary": review.get("summary"),
        "checks": review.get("checks", []) or [],
        "blockers": review.get("blockers", []) or [],
        "layers": layers_out,
        "map": compose_map(review, snapshot),
        "expected_groups": all_slugs,
        "groups": groups_out,
    }


def serialize_for_script(data: dict) -> str:
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


PAGE_PLACEHOLDER_RE = re.compile("|".join(re.escape(p) for p in (PAGE_TITLE_PLACEHOLDER, PAGE_LANG_PLACEHOLDER, PAGE_BODY_PLACEHOLDER)))


def wrap_page(fragment_html: str, review: dict, wrapper_path: str) -> str:
    """Embed the built fragment in the standalone document wrapper.

    The wrapper carries only document-level markup and the control baseline a host would
    otherwise provide; every review element is still created by the fixed widget script.
    All placeholders are substituted in one pass so that inserted text (the title, or review
    data inside the fragment) is never rescanned for another placeholder.
    """
    wrapper = Path(wrapper_path).read_text(encoding="utf-8")
    for placeholder in (PAGE_TITLE_PLACEHOLDER, PAGE_LANG_PLACEHOLDER, PAGE_BODY_PLACEHOLDER):
        if wrapper.count(placeholder) != 1:
            fail(f"page template must contain {placeholder} exactly once")
    values = {
        PAGE_TITLE_PLACEHOLDER: html_escape(str(review.get("title", "")), quote=True),
        PAGE_LANG_PLACEHOLDER: html_escape(review.get("locale", "ja"), quote=True),
        PAGE_BODY_PLACEHOLDER: fragment_html,
    }
    return PAGE_PLACEHOLDER_RE.sub(lambda m: values[m.group(0)], wrapper)


def compute_snapshot_id(snapshot: dict, review: dict) -> str:
    params = snapshot["params"]
    groups = [g["slug"] for g in review.get("groups", [])]
    blockers = [b["id"] for b in review.get("blockers", []) or []]
    core_now, _ = manifest_digest(params["repo"], params["base"], params["untracked"], [], [])
    if core_now != snapshot["core_digest"]:
        fail("the repository state changed after the snapshot was captured; rerun snapshot and re-read the diff")
    digest, _ = manifest_digest(params["repo"], params["base"], params["untracked"], groups, blockers)
    return digest


def cmd_build(args: argparse.Namespace) -> int:
    snapshot = load_json(args.snapshot)
    review = load_json(args.review)
    errors: list[str] = []
    warnings: list[str] = []
    validate_review(review, snapshot, errors, warnings)
    if errors:
        for e in errors:
            print("error: " + e, file=sys.stderr)
        return 2
    for w in warnings:
        print("warning: " + w, file=sys.stderr)
    snapshot_id = compute_snapshot_id(snapshot, review)
    if args.layout == "page" and args.fragment != "full":
        fail("--layout page renders the whole review on one page; split reviews are for the inline widget only")
    fragment = {"kind": args.fragment}
    if args.fragment == "group":
        if not args.groups:
            fail("--groups is required for a group fragment")
        fragment["index"] = args.index
        fragment["total"] = args.total
    only = [s.strip() for s in args.groups.split(",")] if args.groups else None
    approved = [s.strip() for s in args.approved.split(",")] if args.approved else []
    known = {g["slug"] for g in review["groups"]}
    for s in (only or []) + approved:
        if s not in known:
            fail(f"unknown group slug in options: {s}")
    data = compose_widget_data(review, snapshot, snapshot_id, fragment, only, approved, args.layout)
    assets = Path(__file__).resolve().parent.parent / "assets"
    template_path = args.template or str(assets / "review-widget.html")
    template = Path(template_path).read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        fail(f"template must contain {PLACEHOLDER} exactly once")
    html = template.replace(PLACEHOLDER, serialize_for_script(data))
    if args.layout == "page":
        html = wrap_page(html, review, args.page_template or str(assets / "review-page.html"))
    out_path = Path(args.out)
    out_path.write_text(html, encoding="utf-8")
    print(json.dumps({"out": args.out, "absolute": str(out_path.resolve()), "layout": args.layout, "snapshot_id": snapshot_id, "short_id": snapshot_id[:12], "fragment": fragment, "group_order": [g["slug"] for g in data["groups"]], "bytes": len(html.encode("utf-8")), "warnings": warnings}, ensure_ascii=False, indent=1))
    return 0


# ---------------------------------------------------------------------------
# verify subcommand

PAYLOAD_RE = re.compile(r"review_payload_base64:\s*([A-Za-z0-9+/=]+)")


def decode_payload(text: str) -> dict:
    m = PAYLOAD_RE.search(text)
    b64 = m.group(1) if m else text.strip()
    try:
        raw = base64.b64decode(b64, validate=True)
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any decode failure means a malformed payload
        fail(f"payload is not valid Base64 JSON: {exc}")
        return {}


ANCHOR_KEYS = ("path", "hunk", "side", "line")
SIDES = ("old", "new")


def validate_line_anchor(c: dict, errors: list[str]) -> None:
    """Validate the optional line anchor of a comment: all four keys together, or none."""
    present = [k for k in ANCHOR_KEYS if k in c]
    if not present:
        return
    if len(present) != len(ANCHOR_KEYS):
        errors.append("a line comment needs path, hunk, side, and line together")
        return
    if not isinstance(c["path"], str) or not c["path"]:
        errors.append("line comment path must be a non-empty string")
    if not isinstance(c["hunk"], str) or not isinstance(c["path"], str) or not c["hunk"].startswith(c["path"] + "#"):
        errors.append("line comment hunk must be a hunk id of the same path")
    if c["side"] not in SIDES:
        errors.append(f"line comment side must be old or new: {c['side']!r}")
    if isinstance(c["line"], bool) or not isinstance(c["line"], int) or c["line"] < 1:
        errors.append("line comment line must be a positive integer")


def anchored_lines(snapshot: dict) -> set[tuple[str, str, int]]:
    """Every (hunk id, side, line) a reader can comment on: the lines shown in the snapshot diff."""
    lines: set[tuple[str, str, int]] = set()
    for f in snapshot["files"]:
        for hk in f["hunks"]:
            for row in hk["rows"]:
                if row[1] is not None:
                    lines.add((hk["id"], "old", row[1]))
                if row[2] is not None:
                    lines.add((hk["id"], "new", row[2]))
    return lines


def validate_payload(p: dict, errors: list[str]) -> None:
    if p.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {p.get('schema_version')}")
    if p.get("review_action") not in ACTIONS:
        errors.append(f"invalid review_action: {p.get('review_action')}")
    if not isinstance(p.get("snapshot_id"), str) or not HEX64_RE.match(p["snapshot_id"]):
        errors.append("snapshot_id must be 64 lowercase hex characters")
    if not isinstance(p.get("repository"), str) or not p["repository"]:
        errors.append("repository must be a non-empty string")
    for key in ("expected_groups", "approved_groups"):
        v = p.get(key)
        if not isinstance(v, list) or any(not isinstance(s, str) or not SLUG_RE.match(s) for s in v):
            errors.append(f"{key} must be a list of valid slugs")
        elif len(set(v)) != len(v):
            errors.append(f"{key} contains duplicates")
    if isinstance(p.get("expected_groups"), list) and isinstance(p.get("approved_groups"), list):
        unknown = set(p["approved_groups"]) - set(p["expected_groups"])
        if unknown:
            errors.append(f"approved_groups contains groups outside expected_groups: {sorted(unknown)}")
    comments = p.get("comments")
    if not isinstance(comments, list):
        errors.append("comments must be a list")
    else:
        for c in comments:
            if not isinstance(c, dict) or not isinstance(c.get("group"), str) or not isinstance(c.get("body"), str) or not c["body"].strip():
                errors.append("each comment needs a group slug and a non-empty body")
                continue
            if isinstance(p.get("expected_groups"), list) and c["group"] not in p["expected_groups"]:
                errors.append(f"comment refers to a group outside expected_groups: {c['group']}")
            validate_line_anchor(c, errors)
    if p.get("review_action") == "request_changes" and isinstance(comments, list) and not comments:
        errors.append("request_changes requires at least one comment")


def cmd_verify(args: argparse.Namespace) -> int:
    text = Path(args.payload_file).read_text(encoding="utf-8") if args.payload_file else args.payload
    if not text:
        fail("--payload or --payload-file is required")
    result: dict = {"valid": False, "errors": [], "decision": "reject"}
    try:
        payload = decode_payload(text)
    except ToolError as exc:
        result["errors"].append(str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 1
    errors: list[str] = []
    validate_payload(payload, errors)
    result["review_action"] = payload.get("review_action")
    result["snapshot_id_payload"] = payload.get("snapshot_id")
    if errors:
        result["errors"] = errors
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 1
    snapshot = load_json(args.snapshot)
    review = load_json(args.review)
    expected = [g["slug"] for g in review.get("groups", [])]
    blockers = [b["id"] for b in review.get("blockers", []) or []]
    params = snapshot["params"]
    current_id, header = manifest_digest(params["repo"], params["base"], params["untracked"], expected, blockers)
    result["snapshot_id_current"] = current_id
    result["fresh"] = current_id == payload["snapshot_id"]
    result["repository_match"] = header["repository"] == payload["repository"]
    result["expected_groups_match"] = sorted(payload["expected_groups"]) == sorted(expected)
    result["approved_groups"] = payload["approved_groups"]
    result["missing_groups"] = sorted(set(expected) - set(payload["approved_groups"]))
    result["unresolved_blockers"] = blockers
    result["comments"] = payload["comments"]
    known_lines = anchored_lines(snapshot)
    for c in payload["comments"]:
        if "hunk" in c and (c["hunk"], c["side"], c["line"]) not in known_lines:
            result["errors"].append(f"line comment refers to a line outside the snapshot diff: {c['hunk']} {c['side']} {c['line']}")
    if not result["repository_match"]:
        result["errors"].append("payload repository does not match the snapshot repository")
    if not result["expected_groups_match"]:
        result["errors"].append("payload expected_groups differ from the reconstructed group set")
    if result["errors"]:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 1
    result["valid"] = True
    action = payload["review_action"]
    if not result["fresh"]:
        result["decision"] = "stale"
    elif action == "request_changes":
        result["decision"] = "apply_request_changes"
    elif action == "submit_review":
        result["decision"] = "answer_submit_review"
    elif result["missing_groups"] or blockers:
        result["decision"] = "reject_approval"
    else:
        result["decision"] = "accept_approval"
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result["decision"] not in ("stale", "reject_approval") else 1


# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("snapshot", help="capture manifest digest and contextual diff")
    s.add_argument("--repo", default=".", help="path inside the repository")
    s.add_argument("--base", required=True, help="comparison base revision, e.g. origin/main or a commit")
    s.add_argument("--untracked", action="append", help="reviewed untracked file (repository-relative); repeatable")
    s.add_argument("--context", type=int, default=6, help="context lines around each change (default 6)")
    s.add_argument("--function-context", action="store_true", help="expand each hunk to the enclosing function")
    s.add_argument("--out", required=True, help="output snapshot JSON path")
    s.set_defaults(func=cmd_snapshot)

    b = sub.add_parser("build", help="validate review JSON and emit widget HTML")
    b.add_argument("--snapshot", required=True)
    b.add_argument("--review", required=True)
    b.add_argument("--template", help="widget template (default: assets/review-widget.html next to this script)")
    b.add_argument("--layout", choices=LAYOUTS, default="widget", help="widget: inline fragment for the host surface (default); page: standalone two-pane HTML document")
    b.add_argument("--page-template", help="document wrapper for --layout page (default: assets/review-page.html next to this script)")
    b.add_argument("--fragment", choices=FRAGMENT_KINDS, default="full")
    b.add_argument("--groups", help="comma-separated slugs included in a group fragment")
    b.add_argument("--index", type=int, help="fragment position (1-based)")
    b.add_argument("--total", type=int, help="fragment count")
    b.add_argument("--approved", help="comma-separated slugs to pre-check from earlier valid partial approvals")
    b.add_argument("--out", required=True, help="output widget HTML path")
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("verify", help="validate a follow-up payload against the current repository")
    v.add_argument("--payload", help="message text or bare Base64 payload")
    v.add_argument("--payload-file", help="file containing the message text")
    v.add_argument("--snapshot", required=True)
    v.add_argument("--review", required=True)
    v.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        return args.func(args)
    except ToolError as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
