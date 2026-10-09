# Vouch in claude.ai

claude.ai takes skills as single Markdown files (each with its own name and
description) and doesn't accept Python files. These seven files are Vouch split
for it — each is self-contained, and the tools it runs are embedded in it as
code blocks that Claude saves and runs with code execution.

| File | What it does |
|---|---|
| `vouch-corpus.md` | builds your experience corpus from an old CV or from scratch |
| `vouch-record.md` | adds one achievement or job through a guided conversation |
| `vouch-fit.md` | is the posting still open, does it rule you out, how well you fit |
| `vouch-tailor.md` | writes the CV and cover letter from the corpus |
| `vouch-verify.md` | checks every line against the corpus |
| `vouch-ats.md` | simulates an ATS on the CV |
| `vouch-stories.md` | builds interview stories (STAR) anchored to your records |

## Install

1. Download the seven `.md` files from this folder (or from the latest
   [release](https://github.com/leansii/vouch-skills/releases)).
2. Code execution must be available (it is on by default on most plans; if your
   **Settings → Capabilities** shows a *Code execution and file creation*
   toggle, turn it on). Without it the skills still work, just by hand and
   without the code checks.
3. Open **Settings → Customize → Skills**, click **Add** (top right) →
   **Upload a skill**, and select the seven files. Each one becomes its own skill.
4. Make sure all seven show as enabled under **Yours**.

## Use

In a new chat: *"Build my experience corpus from this CV"* (attach it), then
later *"Should I apply to this job? …"* and *"Tailor my resume to this job: …"*
with the posting pasted or linked, and *"Prepare me for the interview"*.
Attach your corpus files at the start of each new chat — claude.ai doesn't keep
files between chats.

Verification runs in the same chat here (claude.ai has no sub-agents), so Vouch
says so in its report; the code checks — a "supported" verdict must cite a real
record, and a figure your corpus never states can't pass — still apply.

These files are generated from `skills/vouch/` by `scripts/build_claude_ai.py`;
don't edit them by hand.
