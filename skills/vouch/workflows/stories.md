# Workflow: interview stories (STAR + Reflection)

For "prepare me for the interview", "what stories should I tell", "build my
story bank". A story retells corpus records in interview shape; it is **never** a
second source of facts. Every story names its `anchors` (record ids), and code
checks it says nothing those records don't.

## Writing stories

1. **Pick the records.** The strongest are ones with a clear before → after,
   the user's own part spelled out (`team:`), and a verifiable metric. One story
   can combine 1–3 records from the same job.
2. **Ask what the records don't hold** — the situation's pressure, a decision
   and its alternatives, what they'd do differently. These are the user's words
   about the facts, not new facts; if an answer adds a fact (a number, a
   technology, a result), add it to the corpus first (`workflows/record.md`).
3. **Draft** into `<corpus>/_stories.md`, format below. Keep attribution exact:
   "I designed it and reviewed every PR; three engineers built it" — interviews
   probe exactly this.
4. **Show, then write**, and run:

```bash
python3 scripts/vouch_corpus.py stories <dir>
```

It fails on an anchor that matches no record and on any figure that no anchored
record states — fix the story, not the check.

## Preparing for a specific posting

```bash
python3 scripts/vouch_corpus.py stories <dir> --jd applications/<company>/jd.txt
```

Lists the stories by how many of the posting's terms their records carry. Pick
4–6 that cover the must-haves and at least one about a failure or conflict, and
note which must-haves no story covers (prepare an honest answer, not a story).

## Format

```markdown
## Stories

### st-001 · Short title
- anchors: [northwind-001]
- tags: [performance, leadership]
- situation: context and stakes, 1–2 sentences
- task: what the user was responsible for
- action: what *they* did (and what others did)
- result: the outcome, figures exactly as the records state them
- reflection: what they learned or would do differently
```

Estimates stay estimates when spoken: "roughly 40 integrations", never "41".
`cannot-confirm` figures don't appear at all. See `examples/corpus/_stories.md`.
