#!/usr/bin/env python3
"""Search company career boards (Greenhouse, Ashby, Lever) for AI and engineering roles,
grouped by the tenant's search categories (see the job-search skill).

No login, no browser, no LinkedIn rate limit. Run it before every job search:

    python3 tools/search_boards.py              # every category in the tenant's boards.json
    python3 tools/search_boards.py <category>   # one category

Output: one line per matching role (category | company | title | location | id | url),
then a per-category count and the list of boards that did not respond.
Slugs that return nothing are reported as DEAD. Keep the slug lists current.
"""
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import tenant

# The boards, location patterns and title pattern are the tenant's own: <tenant>/data/boards.json
#   {"boards": {"<category>": [["gh|ash|lev", "<slug>"], ...]}, "location": {"<category>": "<regex>"}, "title_regex": "<regex>"}
# gh = Greenhouse, ash = Ashby, lev = Lever.
_CFG = {}
try:
    with open(__import__("os").path.join(tenant.root(), "data", "boards.json"), encoding="utf-8") as _f:
        _CFG = json.load(_f)
except (OSError, ValueError):
    sys.exit("error: <tenant>/data/boards.json is missing or invalid. Ask Claude to build it from your categories and target companies.")
BOARDS = {k: [tuple(x) for x in v] for k, v in _CFG.get("boards", {}).items()}
LOCATION = _CFG.get("location", {})
TITLE = re.compile(_CFG.get("title_regex") or r"\b(AI|ML|LLM|Engineer)\b", re.I)


def get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception:
        return None


def fetch(provider, slug):
    """Return a list of (title, location, id, url), or None if the board does not respond."""
    if provider == "gh":
        d = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        if d is None:
            return None
        return [(j["title"], j["location"]["name"], str(j["id"]), j.get("absolute_url", ""))
                for j in d.get("jobs", [])]
    if provider == "ash":
        d = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        if d is None:
            return None
        return [(j["title"], (j.get("location") or "") + (" [remote]" if j.get("isRemote") else ""),
                 j["id"], j.get("jobUrl", "")) for j in d.get("jobs", [])]
    if provider == "lev":
        d = get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        if not isinstance(d, list):
            return None
        return [(j["text"], (j.get("categories") or {}).get("location", ""), j["id"], j.get("hostedUrl", ""))
                for j in d]
    return None


def main(argv):
    wanted = argv[1:] or list(BOARDS)
    unknown = [c for c in wanted if c not in BOARDS]
    if unknown:
        sys.exit(f"Unknown category: {unknown}. Use one of {list(BOARDS)}")
    pairs = sorted({pair for c in wanted for pair in BOARDS[c]})
    with ThreadPoolExecutor(8) as ex:
        results = dict(zip(pairs, ex.map(lambda p: fetch(*p), pairs)))
    dead = [f"{p}:{s}" for (p, s), items in results.items() if items is None]
    for cat in wanted:
        hits = []
        for provider, slug in BOARDS[cat]:
            items = results.get((provider, slug))
            if not items:
                continue
            for title, loc, jid, url in items:
                if TITLE.search(title) and re.search(LOCATION.get(cat, "."), loc or "", re.I):
                    hits.append(f"{cat} | {slug} | {title} | {loc} | {jid} | {url}")
        print(f"== {cat}: {len(hits)} AI/engineering roles in target locations")
        for h in hits:
            print("  " + h)
    print("DEAD (no response, check the slug):", ", ".join(dead) or "none")


if __name__ == "__main__":
    main(sys.argv)
