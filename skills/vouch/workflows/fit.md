# Workflow: should I apply?

For "is this job worth it", "check this posting", "am I a fit", or as the first
step of tailoring. Three checks, all code, a few seconds; the user decides.

## 1. Is the posting still open?

With a URL: `python3 scripts/vouch_fit.py live <url>`. It asks the Greenhouse /
Lever API when the URL is one of theirs, reads the page's JSON-LD `validThrough`,
and looks for "no longer accepting applications"-style text (several languages).
- `closed` → tell the user why and stop unless they want to go on anyway.
- `unknown` (login wall, blocked) → say so; it's not a reason to stop.

No sandbox network (e.g. claude.ai without web access)? Fetch the page with your
web tool, save it, and run `live` on the file.

## 2. Fit and eligibility

Save the posting text as `applications/<company>/jd.txt`, then:

```bash
python3 scripts/vouch_fit.py fit applications/<company>/jd.txt --corpus <dir>
```

It reports:
- **Fit 1–5** — a fixed formula over must-have / nice-to-have coverage and how
  many records answer the posting. ≥ 3 reads "worth tailoring".
- **Covered** and **gaps** — gaps are what the corpus never mentions; they will
  not be written, and the score shows how much that costs.
- **Eligibility** — quoted sentences that may rule the user out: no visa
  sponsorship, must be based in X, a language their `_profile.md` doesn't list.
  Never averaged into the score: a perfect match can still be impossible.

Treat the term lists as a rough cut — the extractor is lexical and lets some
prose through ("single", "page"). Read them, don't recite them.

## 3. Tell the user, briefly

Score, the 3–5 must-haves they clearly have, the real gaps, and any eligibility
quote word for word. Then ask whether to tailor. Never refuse to tailor because
of a low score or a blocker — the user may know something the posting doesn't say.
