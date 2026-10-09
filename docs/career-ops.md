# Vouch + career-ops

[career-ops](https://github.com/career-ops-hq/career-ops) runs the whole job
search: scanning, evaluating offers, tailoring a CV from your `cv.md`, a tracker,
interview prep. Its PDF step already has a code fact gate
(`verify-cv-facts.mjs`) that fails a CV quoting numbers or tools absent from
`cv.md`.

Vouch adds two things that gate can't see:

- **How sure each fact is.** career-ops treats `cv.md` as the truth, and an old
  CV is exactly where an inflated number lives. A Vouch corpus tags every figure
  `verifiable` / `estimate` / `from-cv` / `cannot-confirm`, and the report
  softens or flags lines accordingly.
- **Meaning, not strings.** A separate judge reads each claim against the
  records: "built" where you led the team that built it, Pub/Sub work restated
  as Kafka, e-commerce recast as fintech. Code still decides what each verdict
  means, and rejects a "supported" that cites no record or a figure the corpus
  never states.

## Use them together

1. Install both (each as a Claude Code / Codex / Antigravity plugin).
2. Build your corpus once from the same CV career-ops uses: *"Build my experience
   corpus from cv.md"* (the Vouch corpus workflow interviews you about each
   number).
3. Let career-ops tailor as usual. Then ask: *"Verify the CV career-ops just
   made against my corpus"* — or run it yourself:

```bash
S=<path to skills/vouch>
python3 $S/scripts/vouch_verify.py packet output/cv-<you>-<company>.html \
  --corpus corpus --out verify-packet.md
# judge it in a sub-agent (Claude Code: the vouch-judge agent), then
python3 $S/scripts/vouch_verify.py report verify-packet.md verdicts.jsonl --corpus corpus
```

HTML (`output/*.html`, or a bundle's `cv/tailored/vNNN/cv.html`), Markdown and
plain text all work. Optionally `vouch_ats.py` on the rendered PDF, and
`vouch_fit.py fit jds/<slug>.md --corpus corpus` before tailoring.

Fix what the report flags in career-ops (or in `cv.md`), not by arguing with
the verdict. If a flagged fact is true, add it to the corpus.

## Why not a career-ops plugin

career-ops plugins hook `provider / ingest / search / notify / export`; none of
them runs on a generated CV, and plugins are JavaScript while Vouch's checks are
dependency-free Python that also runs in claude.ai. Until there is a
post-generation hook, the two work side by side as above.
