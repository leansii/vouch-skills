#!/usr/bin/env python3
"""Build single-file skills for claude.ai from skills/vouch/.

claude.ai's uploader treats every .md as its own skill (each needs YAML
frontmatter) and accepts no .py files. So each workflow becomes one
self-contained SKILL file: the shared hard rules, the workflow, the references
it needs, and the scripts it runs embedded as code blocks that Claude writes to
/tmp/vouch/ and runs with code execution.

    python3 scripts/build_claude_ai.py        # writes adapters/claude-ai/*.md
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "vouch"
OUT = ROOT / "adapters" / "claude-ai"

HARD_RULES = SKILL.joinpath("SKILL.md").read_text(encoding="utf-8")
HARD_RULES = HARD_RULES[HARD_RULES.index("## Hard rules"):HARD_RULES.index("## Workflows")].strip()

SKILLS = {
    "vouch-corpus": {
        "description": (
            "Build or extend the user's experience corpus for Vouch: one Markdown file per employer, "
            "one record per achievement, every number tagged by provenance (verifiable / estimate / "
            "from-cv / cannot-confirm) through a short interview. Use when the user wants to set up "
            "their experience for honest resume tailoring, shares an old CV or LinkedIn export to turn "
            "into a corpus, or says 'add this to my corpus'."
        ),
        "workflow": "corpus.md",
        "references": ["corpus-schema.md", "provenance.md"],
        "scripts": ["vouch_common.py", "vouch_corpus.py"],
    },
    "vouch-tailor": {
        "description": (
            "Tailor a CV and cover letter to a job posting using only facts from the user's Vouch "
            "experience corpus: provenance decides wording, attribution stays exact, no gap talk, no "
            "domain recasting. Use when the user pastes a job description or URL and asks for a "
            "tailored resume or cover letter. After drafting, run the vouch-verify and vouch-ats skills."
        ),
        "workflow": "tailor.md",
        "references": ["writing-rules.md", "provenance.md", "corpus-schema.md"],
        "scripts": ["vouch_common.py", "vouch_corpus.py"],
    },
    "vouch-verify": {
        "description": (
            "Check a CV or cover letter line by line against the user's Vouch experience corpus: code "
            "extracts claims and evidence, each claim is judged strictly from the evidence, and code "
            "maps verdicts to keep / soften / flag / remove. Use when the user asks whether their CV "
            "is honest, wants claims checked, or after vouch-tailor drafts a document."
        ),
        "workflow": "verify.md",
        "references": ["provenance.md"],
        "scripts": ["vouch_common.py", "vouch_verify.py"],
    },
    "vouch-ats": {
        "description": (
            "Simulate an applicant-tracking system on a CV: parse it like an ATS, find the job "
            "posting's must-have and nice-to-have keywords, and split what's missing into dropped "
            "facts (the user's corpus has them) and true gaps (it doesn't - never add those). Use for "
            "'ATS check', 'will an ATS find my resume', or after vouch-tailor drafts a CV."
        ),
        "workflow": "ats.md",
        "references": [],
        "scripts": ["vouch_common.py", "vouch_ats.py"],
    },
}

RUN_NOTE = """## Running the tools

The Python tools this skill uses are embedded at the end of this file. When code
execution is available, write each block to `/tmp/vouch/<file name>` exactly as
given (create the folder first), and run them with `python3 /tmp/vouch/...`.
Write the user's corpus files under `/tmp/vouch/corpus/` (or wherever they
uploaded them) and point the tools there. Without code execution, follow the
same steps by hand — the rules they encode are written out above.
"""


def _localize(text: str) -> str:
    """Point workflow commands at /tmp/vouch and references at this file."""
    text = text.replace("python3 scripts/", "python3 /tmp/vouch/")
    text = re.sub(r"`?references/([\w-]+)\.md`?", r"the “\1” section below", text)
    text = re.sub(r"`?workflows/([\w-]+)\.md`?", r"the vouch-\1 skill", text)
    return text


def _demote(md: str) -> str:
    """Shift headings down one level so each part nests under its section.
    Lines inside code fences are left alone (a shell comment is not a heading)."""
    out, fenced = [], False
    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"^#{1,5} ", line):
            line = "#" + line
        out.append(line)
    return "\n".join(out)


def build(name: str, spec: dict) -> str:
    parts = [
        "---",
        f"name: {name}",
        f"description: {spec['description']}",
        "license: MIT",
        "---",
        "",
        f"# {name}",
        "",
        "Part of Vouch (github.com/leansii/vouch-skills): job-tailored resumes where every "
        "line traces to a fact in the user's experience corpus.",
        "",
        _localize(HARD_RULES),
        "",
        _demote(_localize(SKILL.joinpath("workflows", spec["workflow"]).read_text(encoding="utf-8"))),
    ]
    for ref in spec["references"]:
        title = ref.removesuffix(".md")
        body = _localize(SKILL.joinpath("references", ref).read_text(encoding="utf-8"))
        body = re.sub(r"\A# .*\n", "", body).strip()
        parts += ["", f"## {title}", "", _demote(body)]
    if spec["scripts"]:
        parts += ["", RUN_NOTE]
        for script in spec["scripts"]:
            code = SKILL.joinpath("scripts", script).read_text(encoding="utf-8")
            parts += [f"### /tmp/vouch/{script}", "", "```python", code.rstrip(), "```", ""]
    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, spec in SKILLS.items():
        text = build(name, spec)
        (OUT / f"{name}.md").write_text(text, encoding="utf-8")
        print(f"{name}.md  {len(text) // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
