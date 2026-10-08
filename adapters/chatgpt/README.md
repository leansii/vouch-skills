# Vouch in ChatGPT (Custom GPT)

ChatGPT doesn't load Agent Skills folders, so Vouch runs there as a Custom GPT
with the skill's files as knowledge. You lose isolated sub-agents (verification
runs as a separate step in the same chat) but keep the rules and the scripts.

1. ChatGPT → Explore GPTs → Create → Configure.
2. **Instructions:** paste `instructions.md` from this folder.
3. **Knowledge:** upload every file from `skills/vouch/` — `SKILL.md`, the
   `workflows/` and `references/` files, and the `scripts/*.py`.
4. **Capabilities:** enable *Code Interpreter & Data Analysis* (the scripts need it)
   and *Web Search* (for fetching postings).
5. Save as private. In a chat, upload your corpus files (or ask the GPT to build
   them with you) and paste a job posting.

Codex (OpenAI's coding agent) doesn't need this: it reads `AGENTS.md` at the repo
root and runs the scripts directly.
