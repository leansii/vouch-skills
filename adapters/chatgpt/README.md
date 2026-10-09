# Vouch in ChatGPT (Custom GPT)

ChatGPT doesn't load Agent Skills folders, so Vouch runs there as a Custom GPT
with the skill's files as knowledge. You lose isolated sub-agents (verification
runs as a separate step in the same chat) but keep the rules and the scripts.

1. ChatGPT → Explore GPTs → Create → Configure.
2. **Instructions:** paste `instructions.md` from this folder.
3. **Knowledge:** upload every file from `skills/vouch/` — 17 files: `SKILL.md`,
   the 7 `workflows/` and 4 `references/` files, and the 5 `scripts/*.py`
   (within the GPT limit of 20). The names don't collide, so they can sit in one
   flat list. After a Vouch update, replace them all — the scripts and the
   workflows change together.
4. **Capabilities:** enable *Code Interpreter & Data Analysis* (the scripts need it)
   and *Web Search* (for fetching postings).
5. Save as private. In a chat, upload your corpus files (or ask the GPT to build
   them with you) and paste a job posting.

Code Interpreter has no internet access, so the "is this posting still open"
check runs on a page you save and upload (the GPT says so when it needs one).

Codex (OpenAI's coding agent) doesn't need this: it reads `AGENTS.md` at the repo
root and `skills/vouch/` directly (also listed in `.codex-plugin/plugin.json`).
