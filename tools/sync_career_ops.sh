#!/usr/bin/env bash
# Refresh the active tenant's career-ops data root from the tenant's resume, then run career-ops' health check.
# career-ops code lives next to this repo (../career-ops) or in $CAREER_OPS_DIR. Its per-person data lives in
# <tenant>/career-ops/ (CAREER_OPS_ROOT), so tenants never share a cv, profile or tracker.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TENANT_ROOT="$(python3 "$HERE/tools/tenant.py" path)"
CO="${CAREER_OPS_DIR:-$HERE/../career-ops}"
if [ ! -d "$CO" ]; then echo "career-ops not found at $CO (the setup skill installs it)"; exit 1; fi
DATA="$TENANT_ROOT/career-ops"
mkdir -p "$DATA/config" "$DATA/data" "$DATA/modes"
[ -f "$DATA/config/profile.yml" ] || cp "$CO/config/profile.example.yml" "$DATA/config/profile.yml"
[ -f "$DATA/portals.yml" ] || { [ -f "$CO/templates/portals.example.yml" ] && cp "$CO/templates/portals.example.yml" "$DATA/portals.yml"; } || true
[ -f "$DATA/modes/_profile.md" ] || cp "$CO/modes/_profile.template.md" "$DATA/modes/_profile.md"
python3 - "$TENANT_ROOT/resume.md" "$DATA/cv.md" <<'PY'
import re, sys
s = open(sys.argv[1]).read().replace('## Professional Experience', '## Work Experience')
s = re.sub(r'^\*\*(.+?)\*\*, (.+?), ([A-Za-z ]+, [A-Za-z ]+) \| (.+)$',
           lambda m: f"### {m.group(2)} -- {m.group(3)}\n\n**{m.group(1)}**\n{m.group(4)}\n", s, flags=re.M)
open(sys.argv[2], 'w').write(s)
PY
cd "$CO" && CAREER_OPS_ROOT="$DATA" node doctor.mjs | grep -E "⚠|Result" || true
echo "career-ops data root: $DATA (cv.md there is private; keep it out of the engine repo)"
