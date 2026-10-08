# Workflow: ATS check

Simulates what an applicant-tracking system does with the CV: parse the delivered
file into text, then look for the posting's requirements the way a recruiter's
keyword search would. Pure code — run it, don't estimate it.

```bash
python3 scripts/vouch_ats.py <cv.pdf|cv.docx|cv.md> <jd.txt> --corpus <dir> [--title "<job title>"]
```

Check the rendered file when there is one: columns, tables and fonts without a
text layer lose content only there.

## Reading the result

- **Score (0–100)** — 35% parse, 50% must-haves found, 15% nice-to-haves. A proxy
  for "parsed and found", not any vendor's number. Compare drafts with it; don't
  promise it to anyone.
- **Parse failures** — `contact_on_top` (a column layout pushed the email down),
  `sections` (no recognisable Experience/Skills headings), `dated_roles`,
  `clean_text` (garbled font). Fix the layout, not the words.
- **Dropped facts** — requirements the corpus has but the CV doesn't say. Work each
  into the line describing the matching fact, in the posting's wording.
- **True gaps** — requirements the corpus doesn't have. Leave them out. The score
  stays lower; that's the honest number.

The keyword extractor is heuristic: product names from the posting ("Token
Factory") or generic words can appear as requirements. Use judgement on those;
never add a skill to chase one.
