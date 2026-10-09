#!/usr/bin/env python3
"""Should I apply? Three checks before any drafting — pure code, no model calls.

  live  — is the posting still open? (HTTP 404/410, JSON-LD validThrough in the
          past, or the page saying "no longer accepting applications")
  fit   — how much of the posting the corpus can honestly carry: must-have and
          nice-to-have coverage, true gaps, how many records answer it; a 1–5
          score from a fixed formula
  eligibility (part of fit) — sentences that rule the candidate out or decide
          the application: no visa sponsorship, must be based in X, a required
          language the profile doesn't list. Quoted, never averaged into the score.

Nothing here blocks anything: the report goes to the human, who decides.

    python vouch_fit.py fit JD.txt --corpus DIR [--json]
    python vouch_fit.py live URL|FILE [--json]

The closed-posting phrases are adapted from career-ops' liveness-core.mjs
(https://github.com/career-ops-hq/career-ops, MIT License, Copyright (c) 2026
Santiago Fernández de Valderrama). Russian phrases and the eligibility
patterns come from the Vouch bot.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vouch_ats  # noqa: E402
import vouch_common as vc  # noqa: E402

# --- fit ------------------------------------------------------------------------

# Score = 1 + 4 * (COVERAGE * coverage + EVIDENCE * evidence). Coverage leads: a
# posting full of stacks the corpus never touched is the one worth skipping.
# Must-haves weigh 3:1 over nice-to-haves inside coverage.
COVERAGE, EVIDENCE = 0.65, 0.35
MUST_WEIGHT = 0.75
EVIDENCE_FULL_RECORDS = 8  # matching more records means a broad posting, not a better fit
RECOMMEND = 3.0


def _answering_records(terms: list[str], corpus: dict) -> list[str]:
    """Records that state at least one of the posting's terms the corpus knows."""
    out = []
    for r in vc.all_records(corpus):
        text = vc.record_text(r).lower()
        if any(re.search(rf"(?<![\w+#]){re.escape(t)}(?![\w+#])", text) for t in terms):
            out.append(r["id"])
    return out


def assess_fit(jd: str, corpus: dict, profile: dict | None = None) -> dict:
    vocab = vc.vocabulary(corpus)
    must, nice = vouch_ats.split_requirements(jd, vocab)
    known = lambda t: vouch_ats._known_to_corpus(t, vocab)  # noqa: E731
    must_cov = [t for t in must if known(t)]
    nice_cov = [t for t in nice if known(t)]
    gaps = [t for t in [*must, *nice] if not known(t)]

    def share(found: list, of: list) -> float | None:
        return len(found) / len(of) if of else None

    m, n = share(must_cov, must), share(nice_cov, nice)
    if m is None and n is None:
        coverage = 0.0
    elif m is None or n is None:
        coverage = m if n is None else n
    else:
        coverage = MUST_WEIGHT * m + (1 - MUST_WEIGHT) * n
    records = _answering_records(must_cov + nice_cov, corpus)
    # Known only from an employer's stack list: no record says what was done with it.
    texts = [vc.record_text(r).lower() for r in vc.all_records(corpus)]
    rec_vocab = {t.lower() for r in vc.all_records(corpus)
                 for t in [*r["stack"], *r["skills"], *r["jd_keywords"]]}
    thin = [t for t in must_cov + nice_cov
            if not vouch_ats._known_to_corpus(t, rec_vocab)
            and not any(vouch_ats.term_present(t, x) for x in texts)]
    evidence = min(1.0, len(records) / EVIDENCE_FULL_RECORDS)
    score = round(1.0 + 4.0 * (COVERAGE * coverage + EVIDENCE * evidence), 1)
    elig = check_eligibility(jd, profile or {})
    return {
        "score": score, "recommended": score >= RECOMMEND,
        "coverage": round(coverage, 3), "evidence": round(evidence, 3),
        "must": must, "must_covered": must_cov, "nice": nice, "nice_covered": nice_cov,
        "gaps": gaps, "thin": thin, "records": records, "eligibility": elig,
    }


# --- eligibility ------------------------------------------------------------------

_LANGS = ("mandarin|chinese|cantonese|thai|japanese|korean|vietnamese|indonesian|malay|hindi|"
          "arabic|hebrew|turkish|german|french|spanish|portuguese|italian|dutch|polish|czech|"
          "swedish|norwegian|danish|finnish|greek|ukrainian|tagalog|russian|english")
_REGIONS = ("europe|european union|eu|emea|eea|uk|united kingdom|usa|us|united states|"
            "north america|canada|latam|latin america|apac|asia|germany|netherlands|"
            "spain|portugal|france|poland|ireland|israel|india|australia|singapore")
_EUROPE = ("europe eu emea eea uk united kingdom germany netherlands spain portugal france "
           "poland ireland italy austria belgium czech denmark estonia finland greece hungary "
           "latvia lithuania luxembourg norway romania serbia sweden switzerland cyprus "
           "croatia slovakia slovenia bulgaria montenegro georgia armenia")
_RU_LANGS = {"китайск": "chinese", "тайск": "thai", "японск": "japanese", "корейск": "korean",
             "немецк": "german", "французск": "french", "испанск": "spanish",
             "арабск": "arabic", "турецк": "turkish", "английск": "english"}

ELIGIBILITY = {
    "blocker": {
        "sponsorship": [
            r"(?:no|without)\s+(?:visa\s+)?sponsorship",
            r"(?:do(?:es)?\s+not|cannot|can't|will\s+not|won't|unable\s+to)\s+(?:provide|offer|support)?\s*(?:visa\s+)?sponsor",
            r"sponsorship\s+is\s+not\s+(?:available|provided|offered)",
            r"без\s+(?:визовой\s+)?поддержк",
            r"визу?\s+не\s+(?:спонсиру|оформля|предоставля)",
            r"релокац\w*\s+не\s+(?:предусмотрен|оплачива)",
        ],
        "location": [
            r"must\s+be\s+(?:based|located|residing)\s+in",
            r"only\s+(?:considering\s+)?candidates\s+(?:based|located|residing)\s+in",
            r"local\s+(?:hire|candidates)\s+only",
            r"must\s+reside\s+in",
            r"-\s*based\s+only",
            r"только\s+(?:для\s+)?(?:кандидат\w+|резидент\w+)\s+из",
            r"только\s+резидент",
            r"рассматрива\w+\s+только\s+кандидат\w+\s+из",
        ],
    },
    "warning": {
        # Often EEO boilerplate ("authorized to work in the country in which they
        # apply"): it decides the application without saying "no sponsorship".
        "work authorization": [
            r"must\s+(?:already\s+)?(?:be|have)\s+(?:legally\s+)?authorized\s+to\s+work",
            r"must\s+have\s+(?:the\s+)?right\s+to\s+work",
        ],
        # A region the posting hires from — checked against `_profile.md`.
        "location": [
            rf"(?:based|located|living|residing|remote|work(?:ing)?|applicants?|candidates?)\s+"
            rf"(?:anywhere\s+|only\s+)?(?:in|within|from|across)\s+(?:the\s+)?({_REGIONS})\b",
            rf"\bremote\s*[-–—,(/|]?\s*\(?({_REGIONS})\b",
            rf"\b({_REGIONS})[\s-]+(?:based|only|remote)\b",
        ],
        "language": [
            rf"(?:fluent|fluency|native|proficien\w*|speak\w*|command\s+of|knowledge\s+of)\s+(?:in\s+|level\s+|speaker\s+of\s+)?({_LANGS})\b",
            rf"\b({_LANGS})\s+(?:language\s+)?(?:is\s+|are\s+)?(?:required|mandatory|essential)",
            r"(?:свободн\w+|владени\w+)\s+(китайск|тайск|японск|корейск|немецк|французск|испанск|арабск|турецк|английск)\w*",
        ],
    },
    "positive": {
        "sponsorship": [
            r"visa\s+sponsorship\s+(?:is\s+)?(?:available|provided|offered)",
            r"we\s+(?:sponsor|will\s+sponsor)",
            r"relocation\s+(?:package|provided|support|assistance)",
            r"sponsor\w*\s+(?:work\s+)?visas?",
            r"релокац\w+\s+(?:оплачива|предоставля)",
            r"спонсиру\w+\s+визу",
            r"визов\w+\s+поддержк\w+\s+(?:есть|предоставля)",
        ],
    },
}


def _quote(text: str, start: int, end: int, window: int = 70) -> str:
    return " ".join(text[max(0, start - window):end + window].split())


def _profile_languages(profile: dict) -> set[str]:
    """Languages the candidate lists in `_profile.md` (any language name inside)."""
    raw = " ".join(vc._as_list(profile.get("languages"))).lower()
    found = set(re.findall(_LANGS, raw))
    found |= {en for ru, en in _RU_LANGS.items() if ru in raw}
    return found


def _lives_in(region: str, location: str) -> bool:
    """Does the profile's location already sit in the region the posting names?"""
    loc = location.lower()
    if not loc:
        return False
    if region in loc:
        return True
    if region in ("europe", "european union", "eu", "emea", "eea"):
        return any(re.search(rf"\b{c}\b", loc) for c in _EUROPE.split())
    if region in ("us", "usa", "united states"):
        return bool(re.search(r"\b(us|usa|united states)\b", loc))
    return False


def check_eligibility(jd: str, profile: dict) -> dict:
    """{verdict: clear|warning|blocker, findings: [{kind, level, quote}], offers: [...]}"""
    spoken = _profile_languages(profile)
    findings, offers = [], []
    for level, kinds in ELIGIBILITY.items():
        for kind, patterns in kinds.items():
            for pat in patterns:
                m = re.search(pat, jd, re.IGNORECASE)
                if not m:
                    continue
                if kind == "location" and level == "warning":
                    if m.group(1) == "us" or m.group(1) == "Us":  # the pronoun, not the country
                        continue
                    if _lives_in(m.group(1).lower(), str(profile.get("location", ""))):
                        continue
                if kind == "language":
                    lang = m.group(1).lower()
                    lang = _RU_LANGS.get(lang, lang)
                    if lang in spoken or (not spoken and lang in ("english", "russian")):
                        continue
                item = {"kind": kind, "level": level, "quote": _quote(jd, m.start(), m.end())}
                (offers if level == "positive" else findings).append(item)
                break  # one finding per kind is enough to act on
    verdict = "clear"
    if any(f["level"] == "warning" for f in findings):
        verdict = "warning"
    if any(f["level"] == "blocker" for f in findings):
        # "No sponsorship" next to "relocation package": the posting argues with
        # itself (boilerplate vs the real offer) — show both, call it a warning.
        verdict = "warning" if offers else "blocker"
    return {"verdict": verdict, "findings": findings, "offers": offers,
            "contradictory": bool(offers) and any(f["level"] == "blocker" for f in findings)}


def load_profile(corpus_dir: str | Path) -> dict:
    path = Path(corpus_dir).expanduser() / "_profile.md"
    if not path.is_file():
        return {}
    fm, _ = vc.parse_frontmatter(path.read_text(encoding="utf-8"))
    return fm


# --- liveness ---------------------------------------------------------------------

_CLOSED = [re.compile(p, re.IGNORECASE) for p in (
    r"job (is )?no longer available",
    r"job.*no longer open",
    r"\b(?:job|jobs|position|role|posting|opening|vacancy|requisition|req|listing)\b"
    r"[\s\S]{0,60}?(?<!application )(?<!form )has been filled\b(?!\s+out)",
    r"this job has expired",
    r"job posting has expired",
    r"no longer accepting applications",
    r"this (position|role|job) (is )?no longer",
    r"this (?:job|role|position)(?: listing)? is closed\b(?!-)",
    r"job (listing )?not found",
    r"the page you are looking for doesn.t exist",
    r"applications?\s+(?:(?:have|are|is)\s+)?closed",
    r"diese stelle (ist )?(nicht mehr|bereits) besetzt",
    r"offre (expiree|n'est plus disponible)",
    r"(cette )?offre n'est plus (disponible|en ligne|active)",
    r"(offre|poste|annonce) (deja )?pourvu(e)?",
    r"ce poste n'est plus (disponible|a pourvoir|ouvert)",
    r"вакансия (закрыта|в архиве|больше не (доступна|актуальна))",
    r"при[её]м (откликов|резюме|заявок) (закрыт|заверш[её]н|прекращ[её]н)",
)]


def _normalize(text: str) -> str:
    text = re.sub(r"[‘’ʼ′´`]", "'", text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text)


def closed_reason(text: str) -> str | None:
    norm = _normalize(text)
    for pat in _CLOSED:
        m = pat.search(norm)
        if m:
            return m.group(0)
    return None


def expired_valid_through(page: str, now: datetime | None = None) -> str | None:
    """JSON-LD JobPosting.validThrough, when it is in the past."""
    for m in re.finditer(r'"validThrough"\s*:\s*"([^"]+)"', page):
        try:
            when = datetime.fromisoformat(m.group(1).strip().replace("Z", "+00:00"))
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when < (now or datetime.now(timezone.utc)):
            return m.group(1)
    return None


def _api_url(url: str) -> str | None:
    """Greenhouse / Lever postings have a JSON API that answers 404 once closed."""
    gh = re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)/jobs/(\d+)", url)
    if gh:
        return f"https://boards-api.greenhouse.io/v1/boards/{gh.group(1)}/jobs/{gh.group(2)}"
    lv = re.search(r"jobs\.lever\.co/([\w-]+)/([0-9a-f-]{36})", url)
    if lv:
        return f"https://api.lever.co/v0/postings/{lv.group(1)}/{lv.group(2)}"
    return None


def _fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (vouch liveness check)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""


def check_live(target: str) -> dict:
    """{status: open|closed|unknown, reason}. A saved page file works too."""
    path = Path(target).expanduser()
    if not re.match(r"https?://", target) and path.is_file():
        page, code = path.read_text(encoding="utf-8", errors="replace"), 200
    else:
        try:
            api = _api_url(target)
            if api:
                code, _ = _fetch(api)
                if code in (404, 410):
                    return {"status": "closed", "reason": f"the ATS API answers {code}"}
            code, page = _fetch(target)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return {"status": "unknown", "reason": f"could not fetch: {exc}"}
        if code in (404, 410):
            return {"status": "closed", "reason": f"the page answers {code}"}
        if code >= 400:
            return {"status": "unknown", "reason": f"the page answers {code} (blocked or login wall)"}
    expired = expired_valid_through(page)
    if expired:
        return {"status": "closed", "reason": f"validThrough {expired} is in the past"}
    phrase = closed_reason(re.sub(r"<[^>]+>", " ", page))
    if phrase:
        return {"status": "closed", "reason": f"the page says: “{phrase}”"}
    return {"status": "open", "reason": "no sign it is closed"}


# --- report -----------------------------------------------------------------------


def render_fit(r: dict) -> str:
    e = r["eligibility"]
    lines = [f"**Fit {r['score']}/5** — " + ("worth tailoring" if r["recommended"] else
             "the corpus can carry little of this posting; your call"),
             f"- must-have covered {len(r['must_covered'])}/{len(r['must'])}: "
             f"{', '.join(r['must_covered']) or '—'}",
             f"- nice-to-have covered {len(r['nice_covered'])}/{len(r['nice'])}: "
             f"{', '.join(r['nice_covered']) or '—'}",
             f"- gaps (not in your corpus — never claim them): {', '.join(r['gaps']) or 'none'}",
             f"- records that answer it: {len(r['records'])}"]
    if r["thin"]:
        lines.insert(4, f"- thin (only in a stack list, no record says what you did): "
                        f"{', '.join(r['thin'])}")
    if e["findings"]:
        head = {"blocker": "**Eligibility: blocker**", "warning": "**Eligibility: check**",
                "clear": "Eligibility"}[e["verdict"]]
        lines.append(head + (" (the posting contradicts itself)" if e["contradictory"] else ""))
        lines += [f"- {f['kind']}: “…{f['quote']}…”" for f in e["findings"]]
        lines += [f"- offer: “…{o['quote']}…”" for o in e["offers"]]
    else:
        lines.append("Eligibility: nothing found that rules you out")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="vouch_fit", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit")
    f.add_argument("jd", help="job description text file, or - for stdin")
    f.add_argument("--corpus", required=True)
    f.add_argument("--json", action="store_true")
    lv = sub.add_parser("live")
    lv.add_argument("target", help="posting URL, or a saved HTML/text file")
    lv.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "live":
        r = check_live(a.target)
        print(json.dumps(r, ensure_ascii=False) if a.json else f"{r['status']}: {r['reason']}")
        return 0
    r = assess_fit(vc.read_text_arg(a.jd), vc.load_corpus(a.corpus), load_profile(a.corpus))
    if a.json:
        vc.emit(r)
    else:
        print(render_fit(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
