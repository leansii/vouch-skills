#!/usr/bin/env python3
"""Grounding check, code side: claims in, judge packet out; verdicts in, report out.

The model only answers "does this evidence support this claim?" for each
numbered claim. Everything else is code: which lines are claims, what evidence
the judge sees, and what each verdict means for the line (via the provenance
policy in vouch_common).

    python vouch_verify.py packet DOC.md --corpus DIR [--kind cv|letter]
                                   [--company NAME] --out PACKET.md
    python vouch_verify.py report PACKET.md VERDICTS.jsonl --corpus DIR [--json]

`packet` writes the judge packet (instructions + evidence + numbered claims) and
a sidecar PACKET.md.claims.json. The judge — a separate subagent or a fresh
chat that never saw the draft being written — answers one JSON line per claim.
`report` turns those lines into actions: keep / soften / flag / remove_or_verify,
or `unverified` when a line is missing or unreadable (no verdict is not a "no").
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vouch_common as vc  # noqa: E402

# A corpus this small goes to the judge whole: lexical top-k can't match an
# English claim to a Russian record, and a few dozen records fit any context.
FULL_CORPUS_CHARS = 60_000
TOP_K = 6

_BULLET = re.compile(r"^\s*[-*•]\s+(?P<text>.+\S)\s*$")
_WORD = re.compile(r"[a-zа-яё0-9][a-zа-яё0-9+#.\-]*", re.IGNORECASE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[«]?[A-ZА-ЯЁ])")
_SALUTATION = re.compile(r"^(dear|hi|hello|to whom|уважаем|здравствуйте|добрый)\b", re.I)
_CLOSING = re.compile(r"^(sincerely|best|regards|kind regards|yours|thanks|thank you|с уважением)\b", re.I)
_FIRST_PERSON = re.compile(
    r"\b(i|i'm|i've|i'd|i'll|me|my|mine|myself|я|мне|меня|мной|мой|моя|моё|мое|мои|моего|моей|моим|моих)\b",
    re.I,
)
_STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "our", "their", "was",
         "were", "are", "has", "have", "had", "who", "which", "will", "can", "also"}


def strip_frontmatter(md: str) -> str:
    if not md.lstrip().startswith("---"):
        return md
    body = md.lstrip()
    end = body.find("\n---", 3)
    return body[end + 4:] if end != -1 else md


def cv_claims(md: str) -> list[str]:
    """Bullets with 4+ words, outside any section whose heading names skills."""
    claims, in_skills = [], False
    for line in strip_frontmatter(md).splitlines():
        h = re.match(r"^#{1,6}\s+(.*)", line)
        if h:
            in_skills = "skill" in h.group(1).lower() or "навык" in h.group(1).lower()
            continue
        m = _BULLET.match(line)
        if m and not in_skills and len(m.group("text").split()) >= 4:
            claims.append(m.group("text").strip())
    return claims


def letter_claims(md: str, vocab: set[str], company: str = "") -> list[str]:
    """Prose sentences that assert something checkable: a number or a corpus term.
    Sentences about the hiring company (no first person, names it) are skipped —
    they come from the posting, not the corpus."""
    out = []
    for block in strip_frontmatter(md).split("\n\n"):
        lines = [(_BULLET.match(ln).group("text") if _BULLET.match(ln) else ln).strip()
                 for ln in block.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        text = " ".join(lines).strip()
        if not text or _SALUTATION.match(text) or _CLOSING.match(text):
            continue
        for s in _SENTENCE_END.split(text):
            s = s.strip()
            if len(s.split()) < 5:
                continue
            if company and company.lower() in s.lower() and not _FIRST_PERSON.search(s):
                continue
            low = s.lower()
            if re.search(r"\d", s) or any(t in low for t in vocab if len(t) > 2):
                out.append(s)
    return out


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _WORD.findall(text) if t.lower() not in _STOP and len(t) > 2}


def candidates(claim: str, records: list[dict], vocab: set[str], k: int = TOP_K) -> list[str]:
    """Top-k record ids by word overlap, tags counted double."""
    ct = _tokens(claim)
    low = claim.lower()
    terms = {t for t in vocab if t in low}
    scored = []
    for r in records:
        tags = {t.lower() for t in [*r["stack"], *r["skills"], *r["jd_keywords"]]}
        score = len(ct & _tokens(vc.record_text(r))) + 2 * len(tags & terms)
        if score:
            scored.append((score, r["id"]))
    scored.sort(key=lambda x: -x[0])
    return [rid for _, rid in scored[:k]]


def evidence_block(rec: dict) -> str:
    lines = [f"### {rec['id']} · {rec['company']} — {rec['title']}", f"what: {rec['what']}"]
    if rec["stack"]:
        lines.append("stack: " + ", ".join(rec["stack"]))
    for m in rec["metrics"]:
        lines.append(f"metric: {m['value']} ({m['provenance']})")
    if rec["team"]:
        lines.append(f"team: {rec['team']}")  # attribution lives here
    if rec["note"]:
        lines.append(f"note: {rec['note']}")
    lines += rec["extra"]
    return "\n".join(lines)


JUDGE_INSTRUCTIONS = """\
You are a strict grounding checker. You did not write the draft. For each numbered
CLAIM below, decide whether the EVIDENCE records support every fact in it
(technologies, numbers, scope, employer, role).

- Records combine: a claim merging facts from several records is supported when
  each fact is covered by some record (cite the strongest as evidence_id).
- Conservative: a technology, number, outcome or scope word in the claim that no
  record states makes the claim NOT supported.
- Attribution: if the claim says the candidate built/created something but the
  evidence (often a team: or note: line) says a team built it while the candidate
  led, helped or contributed, it is NOT supported.
- A stated analogy ("services on Pub/Sub, the same pattern as Kafka") is supported
  only for the part claimed as done; hands-on work with the analogue needs its own
  evidence. Recasting a fact into a domain or industry it did not have is not supported.
- Claim and evidence may be in different languages: compare meaning, not strings.

Answer with exactly one JSON object per claim, one per line, nothing else:
{"n": 1, "supported": true, "evidence_id": "acme-003", "reason": "short reason"}
Use "evidence_id": null when unsupported.
"""


def build_packet(doc: str, corpus: dict, kind: str, company: str) -> tuple[str, list[dict]]:
    records = vc.all_records(corpus)
    vocab = vc.vocabulary(corpus)
    texts = cv_claims(doc) if kind == "cv" else letter_claims(doc, vocab, company)
    claims = [{"n": i, "text": t, "candidates": candidates(t, records, vocab)}
              for i, t in enumerate(texts, 1)]
    full = sum(len(vc.record_text(r)) for r in records) <= FULL_CORPUS_CHARS
    by_id = {r["id"]: r for r in records}
    out = [JUDGE_INSTRUCTIONS, "## EVIDENCE"]
    if full:
        out += [evidence_block(r) for r in records]
    else:
        ids = []
        for c in claims:
            ids += [i for i in c["candidates"] if i not in ids]
        out += [evidence_block(by_id[i]) for i in ids]
        out.append("(Large corpus: only records that share terms with a claim are listed. "
                   "A claim whose fact is not here is not supported.)")
    out.append("## CLAIMS")
    out += [f"{c['n']}. {c['text']}" for c in claims]
    return "\n\n".join(out) + "\n", claims


def _parse_verdicts(text: str) -> dict[int, dict]:
    found: dict[int, dict] = {}
    for m in re.finditer(r"\{[^{}]*\}", text):
        try:
            d = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict) and "n" in d and "supported" in d:
            sup = d["supported"]
            if isinstance(sup, str):
                sup = sup.strip().lower() in ("true", "yes", "supported")
            d["supported"] = bool(sup)
            found[int(d["n"])] = d
    return found


def build_report(claims: list[dict], verdict_text: str, corpus: dict) -> list[dict]:
    by_id = {r["id"]: r for r in vc.all_records(corpus)}
    verdicts = _parse_verdicts(verdict_text)
    rows = []
    for c in claims:
        v = verdicts.get(c["n"])
        if v is None:
            rows.append({**c, "action": "unverified", "evidence_id": None,
                         "reason": "no readable verdict — check this line yourself"})
            continue
        rec = by_id.get(v.get("evidence_id") or "")
        if not v["supported"]:
            action = vc.GROUNDING["unsupported"]
        else:
            action = vc.GROUNDING.get(vc.claim_provenance(c["text"], rec) or "verifiable", "keep")
        rows.append({**c, "action": action, "evidence_id": v.get("evidence_id"),
                     "reason": str(v.get("reason", ""))})
    return rows


_LABEL = {
    "keep": "✓ supported",
    "soften": "~ supported, estimate — keep the figure soft",
    "flag": "! supported, from an old CV — confirm before sending",
    "remove_or_verify": "✗ no evidence — remove it, or add the fact to your corpus",
    "unverified": "? not checked",
}


def render_markdown(rows: list[dict]) -> str:
    counts = {a: sum(r["action"] == a for r in rows) for a in _LABEL}
    head = (f"**{counts['keep'] + counts['soften'] + counts['flag']} of {len(rows)} lines "
            f"grounded** · {counts['remove_or_verify']} without evidence · "
            f"{counts['unverified']} unchecked")
    lines = [head, ""]
    for r in rows:
        if r["action"] == "keep":
            continue
        lines.append(f"- {_LABEL[r['action']]}: “{r['text']}”")
        lines.append(f"  - {r['reason']}" + (f" (evidence: {r['evidence_id']})" if r["evidence_id"] else ""))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="vouch_verify")
    sub = p.add_subparsers(dest="cmd", required=True)
    pk = sub.add_parser("packet")
    pk.add_argument("doc")
    pk.add_argument("--corpus", required=True)
    pk.add_argument("--kind", choices=("cv", "letter"), default="cv")
    pk.add_argument("--company", default="")
    pk.add_argument("--out", required=True)
    rp = sub.add_parser("report")
    rp.add_argument("packet")
    rp.add_argument("verdicts")
    rp.add_argument("--corpus", required=True)
    rp.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    corpus = vc.load_corpus(a.corpus)
    if a.cmd == "packet":
        text, claims = build_packet(vc.read_text_arg(a.doc), corpus, a.kind, a.company)
        Path(a.out).write_text(text, encoding="utf-8")
        Path(a.out + ".claims.json").write_text(json.dumps(claims, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
        print(f"{len(claims)} claims → {a.out}")
        return 0
    claims = json.loads(Path(a.packet + ".claims.json").read_text(encoding="utf-8"))
    rows = build_report(claims, vc.read_text_arg(a.verdicts), corpus)
    if a.json:
        vc.emit(rows)
    else:
        print(render_markdown(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
