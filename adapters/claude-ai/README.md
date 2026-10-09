# Vouch in claude.ai

claude.ai takes skills as single Markdown files (each with its own name and
description) and doesn't accept Python files. These five files are Vouch split
for it — each is self-contained, and the tools it runs are embedded in it as
code blocks that Claude saves and runs with code execution.

| File | What it does |
|---|---|
| `vouch-corpus.md` | builds your experience corpus from an old CV or from scratch |
| `vouch-record.md` | adds one achievement or job through a guided conversation |
| `vouch-tailor.md` | writes the CV and cover letter from the corpus |
| `vouch-verify.md` | checks every line against the corpus |
| `vouch-ats.md` | simulates an ATS on the CV |

## Install

1. Download the five `.md` files from this folder (or from the latest
   [release](https://github.com/leansii/vouch-skills/releases)).
2. In claude.ai open **Settings → Capabilities** and turn on **Code execution
   and file creation** (the tools need it; without it the skills still work,
   just by hand and without the code checks).
3. Open **Settings → Customize → Skills**, click **Add** (top right) →
   **Upload a skill**, and select the five files. Each one becomes its own skill.
4. Make sure all five show as enabled under **Yours**.

## Use

In a new chat: *"Build my experience corpus from this CV"* (attach it), then
later *"Tailor my resume to this job: …"* with the posting pasted or linked.
Attach your corpus files at the start of each new chat — claude.ai doesn't keep
files between chats.

Verification runs in the same chat here (claude.ai has no sub-agents), so Vouch
says so in its report; the code checks — a "supported" verdict must cite a real
record, and a figure your corpus never states can't pass — still apply.

These files are generated from `skills/vouch/` by `scripts/build_claude_ai.py`;
don't edit them by hand.
