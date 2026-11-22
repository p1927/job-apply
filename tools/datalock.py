"""Shared helpers: cross-process lock for a tenant's data files, atomic file write, name normalising, app id allocator.

One lock file per tenant: <tenant>/data/.lock. Re-entrant inside one process. Works on macOS/Linux (fcntl) and
Windows (msvcrt, untested). Every read-modify-write of data/seen-jobs.csv or data/applications.json must run
inside `with locked(root):` and the lock must cover the READ too, otherwise a parallel agent's rows are lost.
"""
import contextlib, os, re, tempfile, time

_depth = {}


@contextlib.contextmanager
def locked(root, timeout=60):
    lp = os.path.join(root, "data", ".lock")
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    if _depth.get(lp):
        _depth[lp] += 1
        try:
            yield
        finally:
            _depth[lp] -= 1
        return
    fh = open(lp, "a+")
    deadline = time.time() + timeout
    while True:
        try:
            if os.name == "nt":
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if time.time() > deadline:
                fh.close()
                raise SystemExit(f"error: another job-apply tool held {lp} for over {timeout}s. "
                                 "Wait for it to finish, then retry (the lock frees itself when that process exits).")
            time.sleep(0.05)
    _depth[lp] = 1
    try:
        yield
    finally:
        _depth[lp] = 0
        try:
            if os.name == "nt":
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


def atomic_write(p, text, root=None, newline="\n"):
    """Write text to p via a temp file in the same directory, fsync, then os.replace. UTF-8.
    newline="\\n" forces LF; newline="" keeps the text's own line endings. With root, refuses paths outside it."""
    if root is not None:
        rp, rr = os.path.realpath(p), os.path.realpath(root)
        if not (rp == rr or rp.startswith(rr + os.sep)):
            raise SystemExit(f"error: refusing to write outside the tenant folder: {p}")
    d = os.path.dirname(p) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".part", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def norm(s):
    """Lower-case, letters and digits only, single spaces: the one way to compare company and role names."""
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def next_app_id(apps):
    top = max([int(m.group(1)) for a in apps if (m := re.fullmatch(r"APP-(\d+)", str(a.get("id", ""))))] or [0])
    return f"APP-{top + 1:03d}"
