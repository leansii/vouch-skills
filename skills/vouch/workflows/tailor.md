# Workflow: tailor a CV and cover letter to a posting

Inputs: the corpus folder, the job posting (text, file or URL), optionally the
user's master CV and writing samples for voice.

## 1. Get the posting as text

- Pasted text or a file → use it.
- A URL → fetch it with whatever web tool you have. Company career pages are often
  JavaScript-only and return a menu instead of the job: if what you got is short
  (under ~600 characters) or reads like navigation, **don't write from it** — ask
  the user to paste the posting. Hint: a URL with `?gh_jid=<id>` is a Greenhouse
  job; `https://boards-api.greenhouse.io/v1/boards/<company>/jobs/<id>` returns it
  as JSON. Lever: `https://api.lever.co/v0/postings/<company>/<id>`.
- Save it as `applications/<company>/jd.txt`.

## 2. Select facts (before writing anything)

Read the corpus (`python3 scripts/vouch_corpus.py json <dir>` gives it parsed).
Write down, privately:
- the posting's title, company, top 5–8 requirements, must-haves vs nice-to-haves;
- the records that answer them, by id;
- requirements **no** record answers — these are gaps; they will not be written.

Collect the posting's keywords that the selected records really contain (same or
equivalent term in the record's what/stack/skills/jd-keywords). Those — and only
those — may be phrased the posting's way.

## 3. Draft the CV

Take the header (name, contacts, links, education, languages) from the corpus's
`_profile.md`. If it's missing, ask the user for those details — don't leave
placeholders; an ATS can't parse "[email]".

Follow `references/writing-rules.md` and apply provenance per fact. Save as
`applications/<company>/cv.md`.

## 4. Draft the cover letter (if asked)

Same rules, letter shape. Cite only achievements the tailored CV states. Save as
`applications/<company>/cover-letter.md`.

## 5. Verify — a separate pass

Run `workflows/verify.md` on the CV, and on the letter with `--kind letter
--company "<Company>"`. Lines marked **remove_or_verify**: rewrite each once so it
says only what the evidence states, or cut it; then verify again. Don't loop more
than once — show what's left to the user instead.

## 6. ATS check

Run `workflows/ats.md` on the CV (the rendered PDF/DOCX if you built one, else the
markdown). **Dropped facts** — terms the corpus has but the CV doesn't say — are
the only thing to fix here: work them in where the matching fact is described.
**True gaps** stay out.

## 7. Hand over

Show the user, in this order: the CV, the letter, the verification report (with
anything still flagged), the ATS summary, and the gaps you did not write about.
Never say it's ready to send — the user reads it and decides.

## Rendering (optional)

If `pandoc` is available: `pandoc cv.md -o cv.docx` (and `--pdf-engine=xelatex
-o cv.pdf` when a TeX engine exists). Otherwise hand over the markdown; most
editors and Google Docs import it.
