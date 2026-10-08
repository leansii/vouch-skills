#!/usr/bin/env bash
# Build dist/vouch-skill.zip for upload to claude.ai (Settings → Capabilities →
# Skills) or any tool that imports an Agent Skill as a zip.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$root/dist"
rm -f "$root/dist/vouch-skill.zip"
(cd "$root/skills" && zip -qr "$root/dist/vouch-skill.zip" vouch -x '*/__pycache__/*' '*.pyc')
echo "$root/dist/vouch-skill.zip"
