# Vouch

**Job-tailored resumes where every line is something you can vouch for.**

AI resume tools have one failure mode in common: they write a better candidate
than you are. A Kafka you never ran, a fintech you never worked in, "built" where
you led the people who built it. It reads fine, it passes the ATS, and it falls
apart in the first interview.

Vouch is an Agent Skill for Claude, Codex, Gemini CLI / Antigravity and ChatGPT
that tailors your CV and cover letter to a job posting **only from facts you've
recorded**, then checks every line in a separate pass that never saw the draft
being written.

```
$ python3 vouch_ats.py examples/cv-draft.md examples/jd-backend.txt --corpus examples/corpus
ATS score 68.3/100 (proxy, read from md)
  parse 100.0%
  must-have found 66.7% of 15 · nice-to-have 0.0% of 1 · title match: True
  dropped facts (your corpus has them; the CV doesn't say them): payments, api design, mentoring
  true gaps (not in your corpus — never add them): platform, go, rust

$ python3 vouch_verify.py report packet.md verdicts.jsonl --corpus examples/corpus
**4 of 5 lines grounded** · 1 without evidence · 0 unchecked

- ✗ no evidence — remove it, or add the fact to your corpus: “Built event-driven services
  on Kafka that stream parcel status to couriers in under a minute.”
  - Evidence is GCP Pub/Sub, not Kafka; no Kafka work recorded.
- ! supported, from an old CV — confirm before sending: “Integrated Stripe and two local
  card acquirers, increasing checkout conversion by exactly 12%.”
  - Stripe + two local acquirers, conversion up 12%. (evidence: shopkit-001)
```

Real output on the fictional example in `examples/`; the verdicts came from
DeepSeek V4 Flash judging the packet.

The ATS happily counts the invented Kafka as a match. The verification step is
what catches it.

## How it works

1. **Corpus.** Your experience as small Markdown files: one per employer, one
   record per achievement, every number tagged by how sure you are —
   `verifiable`, `estimate`, `from-cv`, `cannot-confirm`. The skill interviews you
   to fill it in and to tag it honestly.
2. **Tailor.** The CV and letter use only records selected for this posting.
   Provenance decides wording: estimates are never printed as precise figures,
   unconfirmed numbers never at all. Attribution stays exact. No gap apologies,
   no recasting your e-commerce work as fintech.
3. **Verify.** Code extracts every claim and the evidence; a judge in a clean
   context (a sub-agent where your tool has them) answers "supported?" per line;
   code maps each verdict through the provenance policy to keep / soften / flag /
   remove. A missing or unreadable verdict is *unverified*, never a silent pass.
4. **ATS check.** Parses the rendered PDF/DOCX the way applicant-tracking systems
   do, finds the posting's must-haves, and splits what's missing into **dropped
   facts** (you have them, the CV didn't say them — fix) and **true gaps** (you
   don't — leave them out). The score can only go up honestly.
5. **You send.** Nothing is submitted, emailed or posted. Ever.

The decisions — what counts as a claim, what evidence the judge sees, what a
verdict means — live in dependency-free Python (`skills/vouch/scripts/`), not in
a prompt. Any model can do the writing and judging.

## Install

| Tool | How |
|---|---|
| **Claude Code** | `/plugin marketplace add leansii/vouch-skills` then `/plugin install vouch@vouch` |
| **claude.ai** | Download `vouch-skill.zip` from [Releases](https://github.com/leansii/vouch-skills/releases) (or `scripts/package.sh`), then Settings → Capabilities → Skills → Upload. Code execution must be on. |
| **Codex / OpenCode / Pi / Cursor** | Clone this repo and open it, or copy `skills/vouch/` into your tool's skills folder. `AGENTS.md` points the agent at the skill. |
| **Gemini CLI / Antigravity** | `gemini extensions install https://github.com/leansii/vouch-skills` (uses `GEMINI.md`), or clone and open the folder. |
| **ChatGPT** | A Custom GPT — see [adapters/chatgpt](adapters/chatgpt/README.md). |

Then: *"Build my experience corpus from this CV"*, and later *"Tailor my resume
to this job: <paste or URL>"*.

Try it without your own data on the fictional example in `examples/`.

## Requirements

Python 3.9+ for the scripts (standard library only). Optional: `pdftotext`
(poppler) for PDF parsing, `pandoc` for DOCX output — both have fallbacks.

## Status

v0.1 — corpus, tailor, verify and ATS workflows. Next: job-fit scoring and
posting-liveness checks, an integration with
[career-ops](https://github.com/santifer/career-ops) to verify the CVs it
generates, and a public eval of how often popular models invent resume lines.

Vouch grew out of a Telegram bot with a measured pipeline (98–99% of generated
lines grounded on its eval set). Some ideas — no gap apologies, honest skill
transfer — were sharpened by career-ops, which is MIT-licensed and worth a look
if you want a full job-search command center.

## License

MIT
