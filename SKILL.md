---
name: nk-memory-with-conditions
description: Write agent memories that say when they hold, and keep the memory directory honest. Use when you are about to save something to Claude Code's auto-memory (MEMORY.md plus one file per memory), when a remembered fact is about to drive a decision, or at the start of a session in a project where several sessions run in parallel. Every memory carries a "Holds when:" line; scripts/memguard.py catches files with no index line, an index close to the silent truncation cap, missing conditions, and sessions sharing one memory directory. Not a note-taking app.
license: MIT
metadata:
  provenance: own practice (2026-07 to 2026-09); no external source
  version: 0.1.0
---
# Memory with conditions

**A memory is an observation made at one moment, not an eternal fact.** Saved without the conditions
under which it was true, it turns into a rule that outlives its cause. One line in a memory once said
"the confirmation popup never opens"; it was true for one remote-control session and it quietly disabled a
working tool for weeks.

## When this applies

- You are writing to `MEMORY.md` or adding a memory file.
- A memory is about to decide something ("we don't use X because…") — verify it first.
- Several sessions run with the same working directory: they share one memory directory.

## Writing a memory

Use `references/memory-template.md`. The non-negotiable line is:

`**Holds when:** <the conditions under which this was observed to be true>`

followed by why (the incident, dated) and how to apply. Three rules:

1. **Conditions, not conclusions.** "The wrapped `grep` skips ignored files" is a conclusion; "holds when
   running inside this session's shell wrapper, not in a script" is the memory.
2. **One example is not a rule.** Write what you saw; if you generalise, say it is a guess and name the
   sample size.
3. **Repeated mistakes are not memory failures.** If the same error happens twice with the memory in
   place, the memory was read and did not help; fix the procedure — add a checkable step where the
   default action happens — instead of writing the incident down a third time.

Before relying on an old memory: check the file, function or flag it names still exists, and whether the
condition still holds. Memories about people and products go stale fastest; keep the date on them.

## The directory

Claude Code keeps auto-memory under `<config dir>/projects/<cwd with / turned into ->/memory/`:
`MEMORY.md` (an index, one line per memory) and one `.md` per memory. Two things about it are not obvious:

- **The index is loaded up to a character cap and silently truncated.** It looks complete; the tail never
  loads. On one machine the cap measured between 24,917 and 29,800 characters (four load snapshots, 2026-09-14);
  the script's default of 24,985 is that measurement, not a documented number — measure yours if you get close.
- **The directory is keyed by cwd, not by session.** Two sessions in the same directory write the same
  files. A read-all → edit → write-all of `MEMORY.md` drops whatever the other session appended in between,
  with no error and a plausible line count.

So: add by appending; edit by anchored replace (assert the anchor occurs exactly once); never rewrite the
whole index while another session may be writing; after writing, check the line count did not shrink.

## The sentinel

`python3 ${CLAUDE_SKILL_DIR}/scripts/memguard.py` (uses the current directory; `--cwd`, `--config-dir`
or `--memory-dir` to point elsewhere; `--quiet` for a session-start hook; `--require-conditions` to make
missing conditions red; `--selftest`).

| Check | Red when | What it means |
|---|---|---|
| A index ↔ files | a file has no index line, or a line has no file | a write was overwritten, or a rename/delete skipped the index |
| B headroom | fewer than 240 characters remain under the cap | the next line you add may be the one that never loads |
| C shared directory | (info only) ≥ 2 live sessions and recent memory writes | use append / anchored replace, not whole-file rewrites |
| D conditions | `--require-conditions` and a memory lacks "Holds when:" | the memory will be read as a rule |

## Boundaries

- It reads the directory; it cannot tell whether a condition is still true.
- The character cap is an observation from one machine and one version; the check is worth keeping
  because the failure mode is silent, but the number is yours to verify.

## Provenance

Own practice, 2026-07 to 2026-09: a memory written without its condition disabled a working tool; two
sessions writing the same index on the same night; an index that loaded half-way with a warning nobody
saw; a limit first assumed to be bytes and corrected to characters by measurement. No external source.
