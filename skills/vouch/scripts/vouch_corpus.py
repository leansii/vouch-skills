#!/usr/bin/env python3
"""Corpus tools: lint it, summarize it, start a new employer file.

    python vouch_corpus.py lint DIR          # problems that would cost you at verify time
    python vouch_corpus.py summary DIR       # what's in it, provenance mix
    python vouch_corpus.py json DIR          # the parsed corpus, for other tools
    python vouch_corpus.py new DIR ID "Company" "Role" START [END]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vouch_common as vc  # noqa: E402

_DATE = re.compile(r"^\d{4}(-\d{2})?$")
# A figure a reader would take as a result: "~600", "40%", "3x", "15 → 100",
# "12,000+". Not dates, versions (v2, Vue 3), names (S3, 2GIS) or years.
_FIGURE = re.compile(r"(?<![\w./-])~?\d[\d,.]*\s?(?:%|x|×|k|\+)?(?![\w/-])")
_YEAR = re.compile(r"^(19|20)\d\d$")


def _figures(text: str) -> list[str]:
    out = []
    for m in _FIGURE.finditer(text):
        tok = m.group(0).strip().rstrip(".,")  # sentence punctuation, not the figure
        digits = re.sub(r"\D", "", tok)
        if _YEAR.match(digits) and tok == digits:
            continue
        if len(digits) >= 2 or tok[-1:] in "%x×k+" or tok.startswith("~"):
            out.append(tok)
    return out


def lint(corpus: dict) -> tuple[list[str], list[str]]:
    """(errors, hints). Errors break verification; hints are worth a look."""
    issues: list[str] = []
    hints: list[str] = []
    seen: dict[str, str] = {}
    for f in corpus["files"]:
        where = f["file"]
        if not f["role"]:
            issues.append(f"{where}: no `role:` in frontmatter")
        for key in ("start", "end"):
            val = f[key]
            if key == "end" and val in ("present", "now", "current"):
                continue
            if val and not _DATE.match(val):
                issues.append(f"{where}: `{key}: {val}` — use YYYY-MM (or `present`)")
        if not f["records"]:
            issues.append(f"{where}: no records under `## Records` — nothing here can be cited")
        for r in f["records"]:
            rid = r["id"]
            if rid in seen:
                issues.append(f"{where}: record id {rid} also used in {seen[rid]} — ids must be unique")
            seen[rid] = where
            if not r["what"]:
                issues.append(f"{where} {rid}: empty `what:` — the judge has nothing to compare against")
            figs = _figures(r["what"])
            if figs and not r["metrics"]:
                hints.append(f"{where} {rid}: `what:` states {', '.join(figs[:3])} but has no tagged "
                             "metric — if it's a result, move it to `metrics:` with a provenance tag")
            for line in r["extra"]:
                if line.startswith("metric (untagged)"):
                    issues.append(f"{where} {rid}: {line} — end it with "
                                  "`· verifiable|estimate|from-cv|cannot-confirm`")
            if not (r["stack"] or r["skills"] or r["jd_keywords"]):
                hints.append(f"{where} {rid}: no stack/skills/jd-keywords — keyword matching can't find it")
    return issues, hints


def summary(corpus: dict) -> str:
    records = vc.all_records(corpus)
    prov = Counter(m["provenance"] for r in records for m in r["metrics"])
    lines = [f"{len(corpus['files'])} files · {len(records)} records · "
             f"{sum(prov.values())} metrics"]
    if prov:
        lines.append("provenance: " + ", ".join(f"{k} {prov[k]}" for k in vc.PROVENANCES if prov[k]))
    for f in corpus["files"]:
        span = f"{f['start']}–{f['end']}" if f["start"] else ""
        lines.append(f"- {f['company']} · {f['role']} {span} · {len(f['records'])} records")
    return "\n".join(lines)


TEMPLATE = """---
company: {company}
id: {id}
role: {role}
location:
start: {start}
end: {end}
domains: []
stack: []
skills: []
---

## Context

One or two sentences: the product, your area, team size.

## Records

### {id}-001 · Short title of one achievement
- what: What you did, in plain words. Who built it if it was a team.
- stack: [technologies used here]
- metrics:
    - the number, as you'd defend it in an interview · estimate
- jd-keywords: [terms a job posting might use for this]
- note: caveats, what you're unsure about
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="vouch_corpus")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("lint", "summary", "json"):
        sub.add_parser(name).add_argument("dir")
    n = sub.add_parser("new")
    n.add_argument("dir")
    n.add_argument("id")
    n.add_argument("company")
    n.add_argument("role")
    n.add_argument("start")
    n.add_argument("end", nargs="?", default="present")
    a = p.parse_args(argv)

    if a.cmd == "new":
        path = Path(a.dir).expanduser() / f"{a.id}.md"
        if path.exists():
            raise SystemExit(f"{path} already exists — edit it instead")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(TEMPLATE.format(id=a.id, company=a.company, role=a.role,
                                        start=a.start, end=a.end), encoding="utf-8")
        print(path)
        return 0
    corpus = vc.load_corpus(a.dir)
    if a.cmd == "json":
        vc.emit(corpus)
    elif a.cmd == "summary":
        print(summary(corpus))
    else:
        issues, hints = lint(corpus)
        for line in issues:
            print("error: " + line)
        for line in hints:
            print("hint:  " + line)
        if not issues:
            print(f"corpus OK ({len(hints)} hints)" if hints else "corpus OK")
        return 1 if issues else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
