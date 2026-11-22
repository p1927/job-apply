#!/usr/bin/env python3
"""Flag AI-sounding wording in the tenant's resume text. Read only.

Usage: python3 tools/check_resume_style.py [config ...]     (default: every config in resume-content.json)
Checks summaries and bullets for banned filler words, dashes used as punctuation and runs of sentences
with the same length. Exits 1 when it finds any.
Rules live in docs/RESUME-GUIDE.md ("Sound human").
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant

BANNED = ["leveraged", "leverage", "spearheaded", "passionate", "synergy", "cutting-edge", "state-of-the-art", "dynamic",
          "results-driven", "proven track record", "seamless", "robust", "innovative", "holistic", "world-class",
          "orchestrated", "championed", "utilized", "utilize", "stakeholders", "best-in-class", "game-changing"]


def texts(node, path=""):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from texts(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from texts(v, f"{path}[{i}]")


def problems(text):
    out = []
    low = text.lower()
    for w in BANNED:
        if re.search(rf"\b{re.escape(w)}\b", low):
            out.append(f"filler word '{w}'")
    if "—" in text or "–" in text:
        out.append("dash used as punctuation")
    sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 3]
    lens = [len(s.split()) for s in sents]
    if len(lens) >= 4 and max(lens) - min(lens) <= 3:
        out.append("all sentences nearly the same length")
    return out


def main():
    cfg = json.load(open(os.path.join(tenant.root(), "resume-content.json"), encoding="utf-8"))
    wanted = sys.argv[1:]
    bad = 0
    for key, node in cfg.items():
        if wanted and key not in wanted:
            continue
        for path, t in texts(node):
            if len(t.split()) < 6:
                continue
            for p in problems(t):
                bad += 1
                print(f"{key}.{path}: {p}: {t[:90]}")
    print(f"{bad} style problem(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
