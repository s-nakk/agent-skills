"""Validate a test-case matrix data file and build the standalone HTML page.

Usage:
    python build_matrix.py <data.json> <out.html>

The page is the fixed template in ../assets/matrix-template.html with the data
embedded as JSON. The script refuses data that the template would render wrong
(an unknown kind, a factor value that is not declared, a missing field) and
prints the totals, the factor values and the combinations that no test covers,
so the caller can report them without re-reading the page.
"""

import json
import sys
from itertools import product
from pathlib import Path

KINDS = {"u", "i", "k", "s"}
OUTCOMES = {"ok", "error"}
MODES = {"plan", "review"}
STATUSES = {"planned", "red", "green"}
ROW_FIELDS = {
    "action": str,
    "outcome": str,
    "result": str,
    "detail": str,
    "kind": str,
    "covers": dict,
    "cases": int,
}


def covered_values(row, factor):
    value = row["covers"].get(factor)
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def validate_factors(section, where, errors):
    factors = section.get("factors")
    if not isinstance(factors, list) or not factors:
        errors.append(f"{where}: 'factors' must be a non-empty list")
        return None
    values_by_factor = {}
    for factor in factors:
        name, values = factor.get("name"), factor.get("values")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{where}: every factor needs a 'name' string")
            continue
        if name in values_by_factor:
            errors.append(f"{where}: factor '{name}' is declared twice")
            continue
        if not isinstance(values, list) or len(values) < 2 or not all(isinstance(v, str) and v.strip() for v in values):
            errors.append(f"{where}: factor '{name}' needs at least two value strings")
            continue
        if len(set(values)) != len(values):
            errors.append(f"{where}: factor '{name}' repeats a value")
            continue
        values_by_factor[name] = values
    return values_by_factor


def validate_combinations(section, where, values_by_factor, errors):
    for ci, combination in enumerate(section.get("combinations", []), 1):
        cwhere = f"{where} combination {ci}"
        names = combination.get("factors")
        if not isinstance(names, list) or len(names) != 2 or names[0] == names[1]:
            errors.append(f"{cwhere}: 'factors' must name two different factors")
            continue
        unknown = [n for n in names if n not in values_by_factor]
        if unknown:
            errors.append(f"{cwhere}: unknown factor {unknown}")
            continue
        for excluded in combination.get("excluded", []):
            values = excluded.get("values")
            if not isinstance(values, list) or len(values) != 2:
                errors.append(f"{cwhere}: every excluded cell needs two 'values'")
                continue
            for name, value in zip(names, values):
                if value not in values_by_factor[name]:
                    errors.append(f"{cwhere}: excluded value '{value}' is not a value of '{name}'")
            if not isinstance(excluded.get("reason"), str) or not excluded["reason"].strip():
                errors.append(f"{cwhere}: excluded cell {values} needs a 'reason'")


def validate_row(row, rwhere, values_by_factor, mode, errors, warnings):
    for field, kind in ROW_FIELDS.items():
        if not isinstance(row.get(field), kind):
            errors.append(f"{rwhere}: '{field}' must be a {kind.__name__}")
    if errors and errors[-1].startswith(rwhere):
        return
    if row["outcome"] not in OUTCOMES:
        errors.append(f"{rwhere}: 'outcome' must be one of {sorted(OUTCOMES)}")
    if row["kind"] not in KINDS:
        errors.append(f"{rwhere}: 'kind' must be one of {sorted(KINDS)}")
    if not row["covers"]:
        errors.append(f"{rwhere}: 'covers' must fix at least one factor value")
    for name, value in row["covers"].items():
        if name not in values_by_factor:
            errors.append(f"{rwhere}: covers an unknown factor '{name}'")
            continue
        values = value if isinstance(value, list) else [value]
        if not values or not all(isinstance(v, str) for v in values):
            errors.append(f"{rwhere}: the value of '{name}' must be a string or a non-empty list of strings")
            continue
        for v in values:
            if v not in values_by_factor[name]:
                errors.append(f"{rwhere}: '{v}' is not a value of '{name}'")
    if row["cases"] < 0:
        errors.append(f"{rwhere}: 'cases' must be 0 or more")
    if row["kind"] == "s" and row["cases"] != 0:
        warnings.append(f"{rwhere}: kind 's' is a test outside the change, so 'cases' should be 0")
    for flag in ("added", "changed"):
        if flag in row and not isinstance(row[flag], bool):
            errors.append(f"{rwhere}: '{flag}' must be true or false")
    if row.get("added") and row.get("changed"):
        errors.append(f"{rwhere}: a row is either 'added' or 'changed', not both")
    if "guard" in row and not isinstance(row["guard"], str):
        errors.append(f"{rwhere}: 'guard' must be a string")
    if "status" in row and row["status"] not in STATUSES:
        errors.append(f"{rwhere}: 'status' must be one of {sorted(STATUSES)}")
    if mode == "plan" and row["kind"] != "s":
        if not row.get("guard"):
            warnings.append(f"{rwhere}: a planned case should say what it confirms, written as a 'must' statement ('guard')")
        if "status" not in row:
            warnings.append(f"{rwhere}: a planned case should carry a 'status' (planned, red or green)")
    if not row["detail"].strip() or not row["result"].strip():
        errors.append(f"{rwhere}: 'result' and 'detail' must not be empty")


def warn_if_diagonal(section, where, values_by_factor, warnings):
    """Several factors that no row ever combines are situations of single tests, not factors.

    A table with one factor (the caller's role, say) has one mark per row by nature, so it is not flagged.
    """
    rows = section["rows"]
    if len(values_by_factor) < 2 or len(rows) < 3:
        return
    marks = [sum(len(covered_values(r, f)) for f in values_by_factor) for r in rows]
    columns = [sum(1 for r in rows if v in covered_values(r, f)) for f, vs in values_by_factor.items() for v in vs]
    if all(m == 1 for m in marks) and all(c <= 1 for c in columns):
        warnings.append(f"{where}: no row fixes more than one value and no value has more than one row; the columns are single tests' situations, so split them into factors and values")


def validate(data):
    errors = []
    warnings = []

    for key, kind in (("title", str), ("scope", str), ("sections", list)):
        if not isinstance(data.get(key), kind):
            errors.append(f"top level: '{key}' must be a {kind.__name__}")
    if errors:
        return errors, warnings

    mode = data.get("mode", "review")
    if mode not in MODES:
        errors.append(f"top level: 'mode' must be one of {sorted(MODES)}")

    for term in data.get("terms", []):
        if not isinstance(term.get("term"), str) or not isinstance(term.get("definition"), str):
            errors.append("terms: every item needs 'term' and 'definition' strings")

    ac = data.get("acceptance_criteria")
    if ac is not None and not (isinstance(ac.get("covered"), int) and isinstance(ac.get("total"), int)):
        errors.append("acceptance_criteria: needs integer 'covered' and 'total'")

    for si, section in enumerate(data["sections"], 1):
        where = f"section {si} ({section.get('title', '?')})"
        if not isinstance(section.get("title"), str):
            errors.append(f"{where}: 'title' must be a string")
        if "placement" in section and not isinstance(section["placement"], str):
            errors.append(f"{where}: 'placement' must be a string")
        if mode == "plan" and not section.get("placement"):
            warnings.append(f"{where}: a plan should name where the tests of this section go ('placement')")
        values_by_factor = validate_factors(section, where, errors)
        if values_by_factor is None:
            continue
        validate_combinations(section, where, values_by_factor, errors)
        rows = section.get("rows")
        if not isinstance(rows, list) or not rows:
            errors.append(f"{where}: 'rows' must be a non-empty list")
            continue
        for ri, row in enumerate(rows, 1):
            validate_row(row, f"{where} row {ri} ({row.get('action', '?')[:40]})", values_by_factor, mode, errors, warnings)
        if not errors:
            warn_if_diagonal(section, where, values_by_factor, warnings)
    return errors, warnings


def summarize(data):
    totals = {"u": 0, "i": 0, "k": 0}
    statuses = {"planned": 0, "red": 0, "green": 0}
    value_gaps = []
    combination_gaps = []
    for section in data["sections"]:
        rows = section["rows"]
        for row in rows:
            if row["kind"] in totals:
                totals[row["kind"]] += row["cases"]
            if row.get("status") in statuses:
                statuses[row["status"]] += row["cases"]
        for factor in section["factors"]:
            for value in factor["values"]:
                if not any(value in covered_values(r, factor["name"]) for r in rows):
                    value_gaps.append(f"{section['title']} / {factor['name']} = {value}")
        values_by_factor = {f["name"]: f["values"] for f in section["factors"]}
        for combination in section.get("combinations", []):
            first, second = combination["factors"]
            excluded = {tuple(e["values"]) for e in combination.get("excluded", [])}
            for a, b in product(values_by_factor[first], values_by_factor[second]):
                if (a, b) in excluded:
                    continue
                if not any(a in covered_values(r, first) and b in covered_values(r, second) for r in rows):
                    combination_gaps.append(f"{section['title']} / {first} = {a} × {second} = {b}")
    return totals, statuses, value_gaps, combination_gaps


def main():
    # The report names factors and values in Japanese; a cp932 console would garble them or fail on a dash
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    data_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    data = json.loads(data_path.read_text(encoding="utf-8"))
    errors, warnings = validate(data)
    for warning in warnings:
        print(f"warning: {warning}")
    if errors:
        for error in errors:
            print(f"error: {error}")
        return 1

    template = (Path(__file__).resolve().parent.parent / "assets" / "matrix-template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    title = data["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    page = template.replace("__TITLE__", title, 1).replace("__DATA_JSON__", payload, 1)
    # open() instead of write_text(newline=...): that argument needs Python 3.10
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(page)

    totals, statuses, value_gaps, combination_gaps = summarize(data)
    report = {
        "out": str(out_path.resolve()),
        "mode": data.get("mode", "review"),
        "cases": {"total": sum(totals.values()), "unit": totals["u"], "integration_stubbed": totals["i"], "integration_real": totals["k"]},
        "uncovered_values": value_gaps,
        "uncovered_combinations": combination_gaps,
    }
    if any(statuses.values()):
        report["status"] = statuses
    # The console encoding depends on the calling shell, so the file is the copy to read
    report_path = out_path.with_name(out_path.name + ".report.json")
    report["report"] = str(report_path.resolve())
    with report_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
