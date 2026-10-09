# How to describe an achievement

A record is only as useful as its detail. Every CV line Vouch writes must trace
back to something a record says, and the verification step compares each line
against the record's exact words. A thin record gives the writer nothing to work
with and the checker nothing to confirm; a rich one gives you strong, specific,
defensible lines for years.

**Ask the user for as much detail as they can give.** Long is good. Half-remembered
is fine — say so, and it gets tagged as an estimate. What hurts is leaving
things out, because what isn't in the corpus can never appear on a CV.

## What to ask about (use as a checklist, not a form)

1. **What was it?** The product or system, who used it, why it mattered.
2. **What did *you* do?** Design, build, lead, review, migrate, fix — the verbs
   that are yours, not the team's.
3. **Who else was involved?** Team size and roles, and where your part ended:
   "3 backend engineers built it; I designed the API and reviewed every PR."
   This one line is what keeps "led" from turning into "built" later.
4. **How?** Technologies, architecture, notable decisions and why.
5. **Scale.** Users, requests, data volume, money, teams, countries.
6. **Before → after.** What changed: speed, cost, errors, time saved, revenue.
7. **How sure are you of each number?** Proof (dashboard, release notes, a
   person who'd confirm it) → `verifiable`; from memory → `estimate`; only in an
   old CV → `from-cv`; can't back it → `cannot-confirm`.
8. **Caveats.** What you're unsure about, what was someone else's idea, what
   didn't work, anything under NDA (what may and may not be named).
9. **Words a job posting would use** for this — they become `jd-keywords`.

## Weak vs strong input (fictional)

**Weak** — what most people write first:

> Worked on payments at Fintrova. Improved performance and helped the team with
> the migration to microservices.

Nothing here can be checked or turned into a strong line: no system, no part
that was theirs, no numbers, no team.

**Strong** — what to aim for:

> At Fintrova (2022–2024) I owned the card-payments service: about 1.2M
> transactions a day for ~300 merchants. It was a Django monolith timing out at
> peak. I proposed splitting authorization out into a Go service behind Kafka,
> wrote the design doc, and built the authorization service myself; two other
> engineers moved settlement and refunds. p99 authorization latency went from
> ~1.8 s to 240 ms (Datadog, I have screenshots). Timeouts at peak dropped from
> roughly 3% to near zero — that one is from memory. I also ran the cut-over
> weekend and wrote the runbook. Settlement still lived in the monolith when I
> left. Under NDA I can name Fintrova but not its bank partners.

Which becomes:

```markdown
### fintrova-003 · Card authorization split out of the payments monolith
- what: Owned the card-payments service (~1.2M transactions/day, ~300 merchants).
  Proposed and designed splitting authorization out of the Django monolith into a
  Go service behind Kafka; wrote the design doc and built the authorization
  service; ran the cut-over weekend and wrote the runbook.
- team: I built authorization; two engineers moved settlement and refunds.
  Settlement stayed in the monolith when I left.
- stack: [Go, Kafka, Django, PostgreSQL, Datadog]
- metrics:
    - p99 authorization latency ~1.8 s → 240 ms · verifiable (Datadog screenshots)
    - peak timeouts ~3% → near zero · estimate
    - ~1.2M transactions/day, ~300 merchants · estimate
- jd-keywords: [payments, microservices, event-driven, Kafka, Go, latency,
    migration, design doc, on-call]
- note: NDA — bank partners may not be named.
```

## Prompt to show the user

When asking for a new achievement, show them something like this (in their
language), so they know long answers are welcome:

> Tell me about it in as much detail as you can — a few paragraphs is perfect.
> What was the product and who used it? What exactly did *you* do, and who else
> worked on it? Which technologies? Any numbers — users, speed, money, time
> saved — and how sure you are of each? Anything you're unsure about or can't
> name publicly? Don't polish it; rough notes are fine. I'll turn it into a
> record and only ask about what's missing.

## Turning input into a record

- One achievement per record. Split a story that covers three things.
- Keep the user's facts and scope exactly; write `what` in plain words.
- Every number goes under `metrics` with its tag; ask when the tag is unclear.
- Attribution goes in `team:`, caveats and NDA limits in `note:`.
- Anything the user corrects later is recorded with the date
  ("clarified by the user, 2026-10-09") — it explains why a line changed.
- Don't fill gaps with plausible text. A known gap belongs in `note:` ("number
  of tenants unknown — ask") or `_gaps.md`.
