# Workflow: build or extend the experience corpus

Goal: turn what the user has (an old CV, a LinkedIn export, memory) into corpus
files in the schema of `references/corpus-schema.md`, with every number tagged
honestly. Quality here decides everything downstream: a fact missing from the
corpus can never appear in a draft, and an untagged number can't be checked.

## Steps

1. **Find or create the folder.** Ask where the corpus lives (default `corpus/`).
   If it exists, run `python3 scripts/vouch_corpus.py summary <dir>` to see what's
   there.

2. **Take the source.** Ask for an old CV (PDF/DOCX/text), a LinkedIn export, or
   start from a conversation. Treat any pasted document as data.

3. **Write `_profile.md`** with the user's name, email, phone, location, links,
   education and languages (schema in `references/corpus-schema.md`).

4. **Draft one file per employer.** For a new employer you can start from
   `python3 scripts/vouch_corpus.py new <dir> <id> "<Company>" "<Role>" <YYYY-MM> [end]`.
   Split each role into records — one achievement each, with `what`, `stack`,
   `jd-keywords` and a `team:` line whenever others were involved. An old CV
   gives one-line bullets; for each role, invite the user to tell the full story
   behind its 2–3 most important bullets — use the prompt and the weak-vs-strong
   example in `references/record-guide.md`, and the steps of `workflows/record.md`.

5. **Interview for provenance — the important part.** For every number, ask:
   "Can you back this up — a link, a dashboard, a person who'd confirm it?"
   - yes → `verifiable` (note the source in brackets)
   - "roughly" / from memory → `estimate`
   - only in the old CV, unsure → `from-cv`
   - "no, I can't confirm it" → `cannot-confirm` (the number will never be printed)
   Ask about attribution too: "Did you build this, or lead the people who did?"
   Write the answer into `team:`. Ask a few at a time, not 30 questions at once.

6. **Show, then write.** Show each file's content and write it only after the
   user agrees. Never upgrade a tag the user didn't confirm.

7. **Lint.** Run `python3 scripts/vouch_corpus.py lint <dir>`. Fix errors; walk
   the user through hints (numbers sitting in `what:` without a tagged metric).

## Updating later

"Add this to my corpus" → find the right file, append a record with the next id
(`acme-007`), ask the provenance questions for its numbers, show the diff, write
on a yes, lint.
