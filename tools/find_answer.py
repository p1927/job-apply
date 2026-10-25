#!/usr/bin/env python3
"""Look up everything the active tenant already knows about a form question, before anyone is asked.

Usage: python3 tools/find_answer.py work authorization permanent right to work
Prints matching lines (file:line) from the tenant's profile, details (including Learned answers), requirements,
and the 'Submitted answers' of every earlier company file. Matches any keyword, ranked by how many match.
Run it for EVERY form question that is not obviously covered, using several wordings (visa, permit, sponsorship, ...).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tenant

FIRST = ("applicant-details.md", "candidate-profile.md", "REQUIREMENTS.md")


def files(root):
    for f in FIRST:
        if os.path.isfile(os.path.join(root, f)):
            yield f
    app = os.path.join(root, "applications")
    if os.path.isdir(app):
        for f in sorted(os.listdir(app)):
            if f.endswith(".md") and not f.endswith("-posting.md"):
                yield os.path.join("applications", f)


def main(words):
    if not words:
        sys.exit(__doc__)
    keys = [w.lower() for w in words if len(w) > 2]
    root = tenant.root()
    hits = []
    for rel in files(root):
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                low = line.lower()
                score = sum(1 for k in keys if re.search(re.escape(k), low))
                if score:
                    hits.append((score, rel, n, line.strip()[:240]))
    hits.sort(key=lambda h: (-h[0], FIRST.index(h[1]) if h[1] in FIRST else 9))
    for score, rel, n, text in hits[:25]:
        print(f"{rel}:{n} [{score}] {text}")
    if not hits:
        print("nothing stored for these words; try other wordings before asking")


if __name__ == "__main__":
    main(sys.argv[1:])
