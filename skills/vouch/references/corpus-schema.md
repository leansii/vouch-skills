# Experience corpus — schema

The corpus is the source of truth. A CV or cover letter is a projection of it:
facts live here once, addressed by ID, and drafts pull them in.

## One file per employer (or project / education block)

File name = a short stable id: `acme.md`, `side-projects.md`. Files starting with
`_` and `README.md` are not parsed as employers (use `_gaps.md` for notes).

## `_profile.md` — who you are

The CV header comes from here, never from a placeholder:

```markdown
name: Alex Example
email: alex@example.com
phone: +351 900 000 000
location: Lisbon, Portugal
links: [linkedin.com/in/alex-example, github.com/alex-example]
languages: [English C1, Portuguese B2]
education: BSc Computer Science, University of Porto, 2018
```

Contact details matter to an ATS: a CV without a parseable email and phone fails
the parse check.

## Frontmatter

```yaml
---
company: Acme Corp          # full name (former name in brackets is fine)
id: acme                    # stable short id, same as the file name
role: Senior Backend Engineer
location: Berlin / Remote
start: 2021-03              # YYYY-MM
end: present                # YYYY-MM or present
domains: [fintech, payments]
stack: [Python 3.11, FastAPI, PostgreSQL, Kubernetes]
skills: [API design, mentoring, incident response]
---
```

## Body

```markdown
## Context

One or two sentences: the product, your area, team size.

## Records

### acme-001 · Payments API rewrite
- what: Led a team of 3 that rewrote the card-payments API from Django to FastAPI.
- stack: [FastAPI, PostgreSQL, Redis]
- metrics:
    - p95 latency 800 ms → 120 ms · verifiable (Grafana screenshot)
    - ~40 internal services migrated · estimate
- team: 3 backend engineers built it; I led design and reviews
- proof: link or "ask me" — optional
- jd-keywords: [payments, API design, migration, latency]
- note: caveats, things you're unsure of
```

Rules the scripts rely on:

- A record header is `### <id> · <title>`; ids are unique across the corpus.
- Fields start at column 0 with `- key:`. Long values may wrap onto the next lines.
- Metrics are indented under `- metrics:`, one per line, ending with
  `· verifiable | estimate | from-cv | cannot-confirm` and an optional `(source)`.
- `stack`, `skills`, `jd-keywords` are bracket lists.
- Any other field (`team:`, `proof:`, `payments:` …) is kept and shown to the judge —
  write attribution in `team:`; it is what stops "led" from turning into "built".

## Provenance tags

See `provenance.md`. Tag every number. A number in `what:` with no tagged metric
can't be checked — `vouch_corpus.py lint` points these out.

## Gaps

What you don't have is information too: note it in `_gaps.md` or a record's
`note:`. Tailoring never fills a gap; it only stops talking about it.
