#!/usr/bin/env python3
"""memguard.py — sentinel for a Claude Code auto-memory directory (MEMORY.md index + one file per memory).

    python3 memguard.py [--cwd PATH] [--config-dir DIR] | [--memory-dir DIR]
                        [--limit CHARS] [--headroom CHARS] [--line-limit LINES] [--line-headroom LINES]
                        [--require-conditions] [--quiet]
    python3 memguard.py --selftest

Resolves the memory dir the way Claude Code does: <config-dir>/projects/<cwd with "/" replaced by "-">/memory
(config-dir defaults to $CLAUDE_CONFIG_DIR or ~/.claude; cwd defaults to the current directory).
Checks:
  A  index ↔ files: a memory file with no index line (someone's write was overwritten, or a file was added without
     its line) and an index line with no file (renamed or deleted without updating the index)           → red
  B  headroom: MEMORY.md is loaded up to a character cap and a line cap, and silently truncated beyond either — the
     index looks complete, the tail is missing. Red when fewer than --headroom characters remain under --limit, or
     fewer than --line-headroom lines remain under --line-limit                                         → red
  C  shared directory: several sessions with the same cwd write the same memory dir; a read-modify-write of the whole
     file silently drops the other session's additions. Reported only as context (see --quiet)         → info
  D  conditions: every memory should say when it holds ("Holds when:", or one of its Chinese equivalents).
     Counted as a warning; red with --require-conditions                                                 → warn/red
Exit: 0 clean · 1 red · 2 selftest failed / dir not found. --quiet prints nothing unless something is red.
Both caps are documented: the Claude Code memory page (code.claude.com/docs/en/memory, read 2026-09-30) says the
first 200 lines of MEMORY.md, or the first 25KB, whichever comes first, are loaded, and that Claude Code measures the
file after each write and tells Claude to shorten it. Check B is therefore a second look, not the only one. The
default --limit (24,985 characters) is a measurement from one machine (2026-09-14: 24,917 characters loaded fully,
29,800 were cut); it counts characters, the documented limit is 25KB, so the two differ on non-ASCII text.
"""
import os, re, sys, tempfile, time
from pathlib import Path

LIMIT, HEADROOM, BUSY_MIN = 24985, 240, 30


def _n(n, word):
    """'1 file', '2 files': a count with its noun in the right number"""
    return f"{n:,} {word}{'' if n == 1 else 's'}"
LINE_LIMIT, LINE_HEADROOM = 200, 5
INDEX_RE = re.compile(r"^- \[[^\]]*\]\(([^)]+\.md)\)", re.M)
COND_RE = re.compile(r"(?im)^(?:\*\*)?(?:holds when|valid when|applies when|成立条件)\b")
PROSE_COND_RE = re.compile(
    r"(?i)\b(?:this|it|the (?:rule|fact|setting|behavio[u]?r))\s+"
    r"(?:is\s+)?(?:only\s+)?(?:true|valid|applicable|applies|holds)\s+"
    r"(?:only\s+)?(?:when|while|if|until)\s+\S+"
)


def has_condition(text):
    """Accept named fields or an explicit prose applicability clause, not arbitrary dates."""
    # Code samples and quoted examples are not conditions on the memory itself.
    text = re.sub(r"(?ms)^\s*(```|~~~).*?^\s*\1\s*$", "", text)
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith('>'))
    return bool(COND_RE.search(text) or PROSE_COND_RE.search(text))


def memory_dir(cwd=None, config_dir=None):
    cwd = os.path.abspath(cwd or os.getcwd())
    cfg = os.path.expanduser(config_dir or os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude")
    return os.path.join(cfg, "projects", cwd.replace("/", "-"), "memory")


def check(mem, limit=LIMIT, headroom=HEADROOM, require_conditions=False, busy_min=BUSY_MIN,
          line_limit=LINE_LIMIT, line_headroom=LINE_HEADROOM):
    """Returns (rc, lines, facts). Shares nothing with the CLI except this function — the selftest calls it too."""
    idx = os.path.join(mem, "MEMORY.md")
    if not os.path.isfile(idx):
        return 2, [f"no MEMORY.md in {mem}"], {}
    with open(idx, encoding="utf-8") as fh:
        body = fh.read()
    files = {f for f in os.listdir(mem) if f.endswith(".md") and f != "MEMORY.md"}
    linked = set(INDEX_RE.findall(body))
    only_file, only_idx = sorted(files - linked), sorted(linked - files)
    n_lines = len(body.splitlines())
    out, rc, facts = [], 0, {"files": len(files), "index": len(linked), "chars": len(body), "room": limit - len(body),
                             "lines": n_lines, "line_room": line_limit - n_lines}
    if only_file or only_idx:
        rc = 1
        out.append(f"🚨 A  index and files disagree: {_n(len(files), 'file')} / {_n(len(linked), 'index line')}")
        if only_file:
            out.append(f"     {len(only_file)} file(s) without an index line: {only_file[:5]}")
            out.append("     → either another session's index write overwrote yours (whole-file rewrite), or a file was added without its line; check timestamps")
        if only_idx:
            out.append(f"     {len(only_idx)} index line(s) without a file: {only_idx[:5]}")
    if facts["room"] < headroom:
        rc = 1
        out.append(f"⚠️ B  MEMORY.md is {len(body):,} chars; cap {limit:,}; only {facts['room']:,} left")
        out.append("     beyond the cap the index is silently truncated — it looks complete, half of it never loads")
        out.append("     → before adding a line, move the longest index lines' text into their own files verbatim; keep one sentence in the index")
        for n, l in sorted(((len(l), l) for l in body.splitlines() if l.startswith("- [")), reverse=True)[:3]:
            out.append(f"       {n:>5} chars  {l[:70]}…")
    if facts["line_room"] < line_headroom:
        rc = 1
        out.append(f"⚠️ B  MEMORY.md is {n_lines:,} lines; line cap {line_limit:,}; only {facts['line_room']:,} left")
        out.append(f"     lines past {line_limit} are silently not loaded — the index looks complete, its last lines never load")
        out.append("     → before adding a line, merge index lines that point to related memories, or move closed ones into a single 'closed' line")
    missing = []
    for f in sorted(files):
        with open(os.path.join(mem, f), encoding="utf-8", errors="replace") as fh:
            if not has_condition(fh.read()):
                missing.append(f)
    facts["no_conditions"] = len(missing)
    if missing:
        if require_conditions:
            rc = 1
        out.append(f"{'🚨' if require_conditions else '·'} D  {len(missing)} memory file(s) do not say when they hold (no 'Holds when:'): {missing[:5]}")
    proj = os.path.dirname(mem)
    now = time.time()
    live = [f for f in os.listdir(proj) if f.endswith(".jsonl") and now - os.path.getmtime(os.path.join(proj, f)) < busy_min * 60] if os.path.isdir(proj) else []
    recent = [f for f in files | {"MEMORY.md"} if now - os.path.getmtime(os.path.join(mem, f)) < busy_min * 60]
    facts["live_sessions"] = len(live)
    if len(live) >= 2 and recent:
        out.append(f"📌 C  {len(live)} sessions active on this cwd in the last {busy_min} min and {len(recent)} memory file(s) written — they share this directory")
        out.append("     add = append; edit = anchored replace (assert the anchor occurs once); never read-all→write-all; afterwards check the line count did not shrink")
    return rc, out, facts


def selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")

    def mk(d, names, index_extra="", cond=True):
        os.makedirs(d, exist_ok=True)
        for n in names:
            Path(d, n + ".md").write_text("---\nname: %s\ndescription: x\n---\n\n%sbody\n" % (n, "**Holds when:** always.\n" if cond else ""))
        Path(d, "MEMORY.md").write_text("# Memory Index\n" + "".join(f"- [{n}]({n}.md) — hook\n" for n in names) + index_extra)

    with tempfile.TemporaryDirectory() as t:
        mem = os.path.join(t, "projects", "-x", "memory")
        mk(mem, ["a", "b"])
        rc, out, f = check(mem)
        chk(rc == 0 and not out and f["files"] == 2 and f["index"] == 2, "control: 2 files / 2 index lines / conditions present → clean, no output")
        Path(mem, "orphan.md").write_text("**Holds when:** always.\n")
        rc, out, f = check(mem)
        chk(rc == 1 and any("without an index line" in l and "orphan.md" in l for l in out), "A: a file without an index line is red and named")
        os.remove(os.path.join(mem, "orphan.md"))
        mk(mem, ["a", "b"], index_extra="- [ghost](ghost.md) — gone\n")
        rc, out, _ = check(mem)
        chk(rc == 1 and any("without a file" in l and "ghost.md" in l for l in out), "A: an index line without a file is red and named")
        mk(mem, ["a", "b"])
        rc, out, f = check(mem, limit=len(Path(mem, "MEMORY.md").read_text()) + 100, headroom=240)
        chk(rc == 1 and any(l.startswith("⚠️ B") for l in out), "B: fewer than headroom chars left is red")
        rc, out, f = check(mem, limit=len(Path(mem, "MEMORY.md").read_text()) + 1000, headroom=240)
        chk(rc == 0, "B control: enough room is clean")
        n = len(Path(mem, "MEMORY.md").read_text().splitlines())
        rc, out, f = check(mem, line_limit=n + 4, line_headroom=5)
        chk(rc == 1 and any(l.startswith("⚠️ B") and "lines" in l for l in out), "B: fewer than line-headroom lines left is red")
        rc, out, f = check(mem, line_limit=n + 5, line_headroom=5)
        chk(rc == 0 and f["lines"] == n, "B control: enough lines left is clean")
        mk(mem, ["m%03d" % i for i in range(199)])
        rc, out, f = check(mem)
        chk(rc == 1 and f["lines"] == 200 and f["chars"] < LIMIT - HEADROOM and any("line cap 200" in l for l in out), "B: a 200-line index well under the character cap is red by the default line cap")
        for i in range(199):
            os.remove(os.path.join(mem, "m%03d.md" % i))
        mk(mem, ["a", "b"])
        mk(mem, ["a", "b"], cond=False)
        rc, out, f = check(mem)
        chk(rc == 0 and f["no_conditions"] == 2 and any(l.startswith("· D") for l in out), "D: missing 'Holds when' is a warning by default")
        rc, out, _ = check(mem, require_conditions=True)
        chk(rc == 1 and any(l.startswith("🚨 D") for l in out), "D: --require-conditions makes it red")
        mk(mem, ["a", "b"])
        proj = os.path.dirname(mem)
        for s in ("s1", "s2"):
            Path(proj, s + ".jsonl").write_text("{}\n")
        rc, out, f = check(mem)
        chk(rc == 0 and f["live_sessions"] == 2 and any(l.startswith("📌 C") for l in out), "C: two live sessions + recent memory writes → info line, not red")
        prose = "The database listens on port 5433. This is only true while we are on the old cluster, until migration."
        chk(has_condition(prose), "D: prose applicability clause is a condition")
        chk(not has_condition("Releases are on 11-02. Always ask the release owner."), "D: a date and an instruction alone are not conditions")
        chk(not has_condition("The grep command skips files that are ignored."), "D: a relative clause is not an applicability condition")
        chk(not has_condition('```\nHolds when: example\n```'), "D: a code example alone is not a condition")
        chk(check(os.path.join(t, "nowhere"))[0] == 2, "a missing directory is exit 2, not a clean 0")
        chk(memory_dir("/tmp/some/proj", os.path.join(t, "cfg")).endswith(os.path.join("projects", "-tmp-some-proj", "memory")), "memory_dir follows the cwd→directory mapping")
    return ok, lines


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__); return 2
    ok, lines = selftest()
    if "--selftest" in argv or not ok:
        print(f"memguard selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    opts, i = {"cwd": None, "config-dir": None, "memory-dir": None, "limit": LIMIT, "headroom": HEADROOM,
               "line-limit": LINE_LIMIT, "line-headroom": LINE_HEADROOM}, 0
    quiet, req = "--quiet" in argv, "--require-conditions" in argv
    while i < len(argv):
        a = argv[i]
        if a.startswith("--") and a[2:] in opts and i + 1 < len(argv):
            opts[a[2:]] = int(argv[i + 1]) if a[2:] in ("limit", "headroom", "line-limit", "line-headroom") else argv[i + 1]; i += 2
        else:
            i += 1
    mem = opts["memory-dir"] or memory_dir(opts["cwd"], opts["config-dir"])
    rc, out, facts = check(mem, opts["limit"], opts["headroom"], req,
                           line_limit=opts["line-limit"], line_headroom=opts["line-headroom"])
    if rc == 2:
        print("\n".join(out)); return 2
    if quiet and rc == 0:
        return 0
    if not quiet:
        print(f"memguard: {mem}")
        print(f"  {_n(facts['files'], 'memory file')} · {_n(facts['index'], 'index line')} · MEMORY.md {facts['chars']:,} chars ({facts['room']:,} under the cap), {_n(facts['lines'], 'line')} ({facts['line_room']:,} under the line cap) · {facts['no_conditions']} without conditions")
    print("\n".join(l for l in out if not (quiet and l.startswith("📌"))))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
