# Vouch — instructions for Gemini CLI / Antigravity

This extension provides the **Vouch** skill: honest, job-tailored resumes and
cover letters where every line traces to the user's experience corpus.

When the user asks to build an experience corpus, tailor a CV or cover letter to a
job posting, check a CV for unsupported claims, or run an ATS check: read
`skills/vouch/SKILL.md` and follow it. Workflows: `skills/vouch/workflows/`.
Rules: `skills/vouch/references/`. Tools (Python 3, no dependencies):
`skills/vouch/scripts/`.

For verification, judge the packet in a fresh session or sub-agent that receives
only the packet file, so it never sees how the draft was written.
