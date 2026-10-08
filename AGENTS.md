# Vouch — instructions for coding agents (Codex, Pi, OpenCode, Cursor, …)

This repository is the **Vouch** skill: honest, job-tailored resumes and cover
letters where every line traces to the user's experience corpus.

When the user asks to build an experience corpus, tailor a CV or cover letter to a
job posting, check a CV for unsupported claims, or run an ATS check: read
`skills/vouch/SKILL.md` first and follow it. Its workflows live in
`skills/vouch/workflows/`, its rules in `skills/vouch/references/`, and its
dependency-free Python tools in `skills/vouch/scripts/` (run with `python3`).

For the verification step, run the judge as a separate sub-task or worker that
receives only the packet file (`codex exec`, a fresh session, or your tool's
sub-agent feature) so it never sees how the draft was written. Never fill the
verdicts file with blanket "supported" lines — the report rejects verdicts that
cite no corpus record.
