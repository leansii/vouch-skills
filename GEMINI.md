# Vouch — instructions for Gemini CLI / Antigravity

This extension provides the **Vouch** skill: honest, job-tailored resumes and
cover letters where every line traces to the user's experience corpus.

When the user asks to build an experience corpus, tailor a CV or cover letter to a
job posting, check a CV for unsupported claims, run an ATS check, decide whether
a posting is worth applying to, or prepare interview stories: read
`skills/vouch/SKILL.md` and follow it. Workflows: `skills/vouch/workflows/`.
Rules: `skills/vouch/references/`. Tools (Python 3, no dependencies):
`skills/vouch/scripts/`.

For verification, judge the packet with `invoke_subagent` (one subagent per
packet), so the judge never sees how the draft was written. Its prompt, in full:

> Read `<packet path>`. Follow its instructions exactly. Do not run commands or
> open any other file. Write one JSON line per claim, nothing else, to
> `<verdicts path>`, then reply with how many claims you judged and how many were
> unsupported.

Then wait for the subagent's completion message — don't poll and kill it. If it
waits for a permission, ask the user to approve. Only if subagents are
unavailable, judge the packet yourself claim by claim and tell the user it ran in
the same conversation. Never fill the verdicts file with blanket "supported"
lines — the report rejects verdicts that cite no corpus record.
