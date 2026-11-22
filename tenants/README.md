# tenants/

One folder per person, created by the setup skill (`python3 tools/tenant.py create "Full Name"`). Everything in a person's folder is private to them and ignored by this repo. `_template/` is copied for each new person. `.active` names the person the tools work for.

A tenant's `data/` holds the ledger, applications, search queue, boards, vocab overrides, `platform-accounts.md` and `backlog-*.md` files.
