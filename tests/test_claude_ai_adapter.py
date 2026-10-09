"""The claude.ai single-file skills: generated from skills/vouch, and the tools
embedded in them run once written out the way the skill tells Claude to."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "adapters" / "claude-ai"
NAMES = ("vouch-corpus", "vouch-tailor", "vouch-verify", "vouch-ats")


def _blocks(md: str) -> dict[str, str]:
    return dict(re.findall(r"### /tmp/vouch/(\S+\.py)\n\n```python\n(.*?)\n```", md, re.S))


def test_generated_files_are_up_to_date(tmp_path):
    before = {n: (OUT / f"{n}.md").read_text(encoding="utf-8") for n in NAMES}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_claude_ai.py")], check=True,
                   capture_output=True)
    after = {n: (OUT / f"{n}.md").read_text(encoding="utf-8") for n in NAMES}
    assert before == after, "run scripts/build_claude_ai.py and commit the result"


def test_each_file_is_a_valid_standalone_skill():
    for n in NAMES:
        md = (OUT / f"{n}.md").read_text(encoding="utf-8")
        assert md.startswith(f"---\nname: {n}\ndescription: ")
        assert "## Hard rules" in md
        assert "python3 scripts/" not in md


def test_embedded_tools_run_from_tmp(tmp_path):
    md = (OUT / "vouch-verify.md").read_text(encoding="utf-8")
    for name, code in _blocks(md).items():
        (tmp_path / name).write_text(code, encoding="utf-8")
    cv = ROOT / "examples" / "cv-draft.md"
    out = tmp_path / "packet.md"
    r = subprocess.run([sys.executable, str(tmp_path / "vouch_verify.py"), "packet", str(cv),
                        "--corpus", str(ROOT / "examples" / "corpus"), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "6 claims" in r.stdout and out.exists()
