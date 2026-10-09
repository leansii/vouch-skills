# Workflow: verify a CV or cover letter against the corpus

Every checkable line is judged against the corpus **in a context that did not
write it**. Code picks the claims and the evidence and decides what each verdict
means; the judge only answers "is this supported?".

## 1. Build the judge packet

```bash
python3 scripts/vouch_verify.py packet <cv.md> --corpus <dir> --out <applications/x/verify-packet.md>
# cover letter: add  --kind letter --company "<Company>"
```

The packet holds the judge instructions, the evidence (the whole corpus when it's
small, else the records that share terms with each claim) and numbered claims.

## 2. Judge in a clean context

Pick the strongest isolation your environment offers:

1. **A separate agent / subagent** with no access to this conversation (in Claude
   Code: the `vouch-judge` agent; in Antigravity: `invoke_subagent`; elsewhere, any
   "run a sub-task" facility). Give it only the packet path and the verdicts path,
   and tell it to read the packet and write the file — no commands. It writes one
   JSON line per claim to `verdicts.jsonl`. **Wait for it to finish** (it can take
   a few minutes); if it stops to ask for a permission, ask the user to approve it.
   Never stop a judge and fill in its verdicts yourself.
2. **No sub-agents** (e.g. a plain chat): judge the packet yourself as a distinct
   step — read only the packet, forget the drafting rationale, answer each claim
   strictly from the evidence text. Say to the user that this pass ran in the same
   conversation.
3. **No code execution:** do the same by hand: list the bullets (CV) or the
   sentences with numbers/technologies (letter), and judge each against the corpus.

**Never write verdicts without judging each claim against the evidence.** A
"supported" verdict must cite the id of a real record; the report rejects any
that doesn't (e.g. `"evidence_id": "manual"`) and shows the line as unverified.
If you can't run a separate judge, say so and judge each claim yourself — a
bulk "all supported" is a failed check, not a pass.

Verdict format, one line per claim, nothing else:
`{"n": 3, "supported": false, "evidence_id": null, "reason": "no record mentions Kafka"}`

## 3. Report

```bash
python3 scripts/vouch_verify.py report <verify-packet.md> <verdicts.jsonl> --corpus <dir>
```

Actions, decided by code from the verdict and the evidence record's provenance:

| Action | Meaning | What to do |
|---|---|---|
| keep | supported by a verifiable fact | nothing |
| soften | supported, but the fact is an estimate | no precise figure |
| flag | supported by an unconfirmed (`from-cv`) fact | tell the user |
| remove_or_verify | no evidence | rewrite to what the evidence says, cut it, or add the fact to the corpus if it's true |
| unverified | no readable verdict | the user checks it by eye |

Show the report to the user as is. Don't argue a verdict away; if the user says a
flagged fact is true, the fix is a corpus record (workflows/corpus.md), not a
rewrite of the verdict.
