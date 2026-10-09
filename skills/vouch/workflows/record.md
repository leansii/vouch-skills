# Workflow: add an achievement to the corpus

For "add this to my experience", "I want to describe a project", "help me write
up what I did at X". One conversation, one or more records, written only after
the user agrees. Read `references/record-guide.md` first — it has the question
checklist, the weak-vs-strong example and the prompt to show the user.

## Steps

1. **Find the corpus and the employer.** Ask where the corpus folder is (default
   `corpus/`). Which employer or project is this? If its file doesn't exist yet,
   create it: `python3 scripts/vouch_corpus.py new <dir> <id> "<Company>" "<Role>" <YYYY-MM> [end]`
   (ask for role and dates).

2. **Invite a long answer.** Show the prompt from `references/record-guide.md`
   (in the user's language) and the strong example if they seem unsure what
   "detail" means. Let them write freely.

3. **Fill gaps with a few targeted questions** — at most 3–4 at a time, only for
   what's missing from the checklist: their exact part vs the team's, scale,
   before/after, and the source of each number.

4. **Tag every number.** For each figure ask, if it isn't already clear: "Can you
   back this up — a dashboard, a link, someone who'd confirm it?" →
   `verifiable` / `estimate` / `from-cv` / `cannot-confirm`. Never pick the tag for
   them.

5. **Draft the record(s).** Next free id in that file (`acme-007`); schema in
   `references/corpus-schema.md`. One achievement per record.

6. **Show, then write.** Show the record exactly as it will be saved, plus what
   you were unsure about. Write only on a yes. Then
   `python3 scripts/vouch_corpus.py lint <dir>` and fix what it reports.

7. **Offer the next one.** "Anything else from <employer>? Most people have 5–10
   records per job." A corpus with a handful of rich records per role beats a long
   list of one-liners.

## Editing an existing record

Show the current record, apply the user's correction, and add a dated note
("clarified by the user, 2026-10-09: …") when the change alters a fact. Never
renumber records — verification reports and drafts refer to their ids.
