"""Shared, dependency-free helpers for the Vouch scripts.

Python 3.9+ standard library only: the same files run in Claude Code, claude.ai's
code sandbox, Codex, Gemini CLI and a bare terminal. Nothing here calls a model.

The corpus is a folder of Markdown files, one per employer or project
(schema: references/corpus-schema.md). This module parses it into plain dicts
and holds the provenance policy — the table that decides what may be said about
a fact. Decisions live here, in code, never in a prompt.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROVENANCES = ("verifiable", "estimate", "from-cv", "cannot-confirm")

# What a draft may do with a fact when it surfaces (before generation).
SURFACE = {
    "verifiable": "keep",  # use freely, exact numbers included
    "estimate": "soften",  # may appear, never as a precise figure
    "from-cv": "flag",  # unconfirmed: use cautiously, flag if load-bearing
    "cannot-confirm": "narrative",  # the figure never reaches a draft; prose only
}
# What the verification step does AFTER generation, from (verdict, provenance).
GROUNDING = {
    "unsupported": "remove_or_verify",
    "verifiable": "keep",
    "estimate": "soften",
    "from-cv": "flag",
    "cannot-confirm": "flag",
}
# Most cautious first wins when a record mixes provenances.
_CAUTION = ["verifiable", "estimate", "from-cv", "cannot-confirm"]

_RECORD_HEADER = re.compile(r"^###\s+(?P<id>[^\s·]+)\s*·\s*(?P<title>.+?)\s*$")
_FIELD = re.compile(r"^-\s*(?P<key>[a-zA-Z][\w-]*):\s*(?P<val>.*)$")
_METRIC = re.compile(
    r"^\s*-\s*(?P<val>.+?)\s*·\s*(?P<prov>verifiable|estimate|from-cv|cannot-confirm)"
    r"(?:\s*(?P<src>\(.+\)))?\s*$"
)
_LIST_KEYS = {"stack", "skills", "jd-keywords", "jd_keywords", "domains"}


# --- frontmatter: a tiny YAML subset (flat keys, inline or block lists) --------


def _scalar(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def bracket_list(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [_scalar(x) for x in raw.split(",") if x.strip()]


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """(fields, body). Supports `key: value`, `key: [a, b]` and `key:` followed
    by `- item` lines — all the corpus schema uses."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fields: dict = {}
    current: str | None = None
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", line) or re.match(r"^-\s+(.*)$", line)
        if item and current is not None:
            fields.setdefault(current, [])
            if isinstance(fields[current], list):
                fields[current].append(_scalar(item.group(1)))
            continue
        kv = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).split(" #")[0].strip()
        current = key
        if val.startswith("["):
            fields[key] = bracket_list(val)
        elif val:
            fields[key] = _scalar(val)
        else:
            fields[key] = []
    return fields, text[end + 4 :].lstrip("\n")


# --- corpus ---------------------------------------------------------------------


def _flush_metric(rec: dict, buf: list[str]) -> None:
    if not buf:
        return
    text = " ".join(buf)
    buf.clear()
    m = _METRIC.match(text)
    if not m:
        leftover = text.lstrip("- ").strip()
        if leftover:  # an unreadable tag is no reason to lose the fact
            rec["extra"].append(f"metric (untagged): {leftover}")
        return
    value = m.group("val").strip()
    src = (m.group("src") or "").strip()
    rec["metrics"].append({"value": f"{value} {src}".strip(), "provenance": m.group("prov")})


def parse_records(body: str, company_id: str, company: str) -> list[dict]:
    parts = body.split("## Records", 1)
    if len(parts) < 2:
        return []
    records = []
    for block in re.split(r"(?m)^###\s+", parts[1])[1:]:
        header, _, rest = block.partition("\n")
        m = _RECORD_HEADER.match("### " + header.strip())
        if not m:
            continue
        rec = {
            "id": m.group("id").strip(), "title": m.group("title").strip(),
            "company_id": company_id, "company": company, "what": "",
            "stack": [], "skills": [], "jd_keywords": [], "metrics": [],
            "note": "", "team": "", "extra": [],
        }
        in_metrics = False
        metric_buf: list[str] = []
        cont: list[str] | None = None
        fields: dict[str, list[str]] = {}
        for raw in rest.splitlines():
            if raw.startswith("## "):  # next section of the file
                break
            s = raw.strip()
            # Fields start at column 0; indented "- x · estimate" lines are metrics.
            fm = _FIELD.match(s) if not raw[:1].isspace() else None
            if in_metrics and not fm:
                if s.startswith("-"):
                    _flush_metric(rec, metric_buf)
                    metric_buf.append(s)
                elif s:
                    metric_buf.append(s)
                continue
            if fm:
                if in_metrics:
                    _flush_metric(rec, metric_buf)
                in_metrics = False
                key, val = fm.group("key").lower(), fm.group("val").strip()
                if key == "metrics":
                    in_metrics = True
                    cont = None
                    if val:  # "- metrics: 40% faster · estimate" on one line
                        metric_buf.append("- " + val)
                        in_metrics = True
                    continue
                cont = fields.setdefault(key, [])
                cont[:] = [val]
                continue
            if cont is not None and s:
                cont.append(s)
        if in_metrics:
            _flush_metric(rec, metric_buf)
        for key, lines in fields.items():
            joined = " ".join(lines).strip()
            if key in _LIST_KEYS:
                rec[key.replace("-", "_")] = bracket_list(joined)
            elif key in ("what", "note", "team"):
                rec[key] = joined
            else:  # payments:, proof:, hosting: … — keep, the judge needs them
                rec["extra"].append(f"{key}: {joined}")
        records.append(rec)
    return records


def load_corpus(root: str | Path) -> dict:
    """Parse every `*.md` in the corpus folder (README/underscore files skipped)."""
    root = Path(root).expanduser()
    if not root.is_dir():
        raise SystemExit(f"corpus folder not found: {root}")
    files = []
    for path in sorted(root.glob("*.md")):
        if path.name.lower() == "readme.md" or path.name.startswith("_"):
            continue
        fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        cid = str(fm.get("id") or path.stem)
        company = str(fm.get("company") or cid)
        ctx = re.search(r"(?ms)^## Context\s*\n(.*?)(?=^## |\Z)", body)
        files.append({
            "file": path.name, "id": cid, "company": company,
            "role": fm.get("role", ""), "start": str(fm.get("start", "")),
            "end": str(fm.get("end", "")), "location": fm.get("location", ""),
            "domains": _as_list(fm.get("domains")), "stack": _as_list(fm.get("stack")),
            "skills": _as_list(fm.get("skills")),
            "context": (ctx.group(1).strip() if ctx else ""),
            "records": parse_records(body, cid, company),
        })
    return {"root": str(root), "files": files}


def _as_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(x) for x in val if str(x).strip()]
    return [str(val)] if val else []


def all_records(corpus: dict) -> list[dict]:
    return [r for f in corpus["files"] for r in f["records"]]


def record_provenance(rec: dict | None) -> str | None:
    """The record's MOST cautious metric provenance (None: no metrics)."""
    if not rec or not rec["metrics"]:
        return "verifiable" if rec else None
    return max((m["provenance"] for m in rec["metrics"]), key=_CAUTION.index)


# A figure: digits not glued to letters ("A100", "FP8", "S3" are names, not
# metrics). Single digits count only with a unit sign ("4x", "3%"): "a team of
# 4" style counts are checked by the judge, and bare digits collide by chance;
# a scale word or suffix ("5 million", "3k") makes a single digit a figure.
_NUM = re.compile(
    r"(?<![A-Za-z\d])(\d+(?:[.,]\d+)?)"
    r"(\s?(?:[%x×]|million|billion|thousand|млн|млрд|тыс)|[kKmM](?![A-Za-z]))?(?![A-Za-z\d])"
)


_YEAR = re.compile(r"^(19[5-9]\d|20[0-4]\d)$")


def _numbers(text: str) -> set[str]:
    """Figures in a text. Years are dates, checked against employer dates — not
    metrics ("working in Python since 2018" has nothing to soften)."""
    out = set()
    for num, unit in _NUM.findall(text):
        num = num.replace(",", "")
        if _YEAR.match(num) or (len(num) == 1 and not unit):
            continue
        out.add(num)
    return out


def claim_provenance(claim: str, rec: dict | None) -> str | None:
    """Provenance of what a claim actually says, not of its whole record.

    Provenance tags figures, so it is read off the metrics whose numbers the
    claim repeats: "p95 900 ms -> 140 ms" from a verifiable metric stays
    verifiable even if the same record also holds an estimate. A claim with no
    figure has nothing to soften. A figure that matches no metric falls back to
    the record's most cautious tag.
    """
    if rec is None:
        return None
    nums = _numbers(claim)
    if not nums:
        return "verifiable"
    matched = [m["provenance"] for m in rec["metrics"] if nums & _numbers(m["value"])]
    if matched:
        return max(matched, key=_CAUTION.index)
    return record_provenance(rec)


def record_text(rec: dict) -> str:
    """Everything a record states, as one searchable string."""
    parts = [rec["title"], rec["what"], *(m["value"] for m in rec["metrics"]),
             *rec["stack"], *rec["skills"], *rec["jd_keywords"], rec["note"],
             rec["team"], *rec["extra"]]
    return " ".join(p for p in parts if p)


def vocabulary(corpus: dict) -> set[str]:
    vocab: set[str] = set()
    for f in corpus["files"]:
        vocab.update(t.lower() for t in [*f["stack"], *f["skills"], *f["domains"]])
        for r in f["records"]:
            vocab.update(t.lower() for t in [*r["stack"], *r["skills"], *r["jd_keywords"]])
    return vocab


# --- io -------------------------------------------------------------------------


def emit(obj) -> None:
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def read_text_arg(path: str) -> str:
    return sys.stdin.read() if path == "-" else Path(path).expanduser().read_text(encoding="utf-8")
