# nk-memory-with-conditions

A [Claude Code](https://code.claude.com) skill. Write agent memories that say when they hold, and keep the memory directory honest.

Part of [nickkk-skills](https://github.com/NickkkLian/nickkk-skills) — skills that stop an AI coding agent's
"done, tested, safe" from being taken on faith.

## What it does

- Template: every memory carries `**Holds when:**`, a dated why, and a checkable how-to-apply.
- `scripts/memguard.py`: index ↔ files mismatch, headroom before the index is silently truncated, memories without conditions, and sessions that share one memory directory (same cwd).
- Append-only and anchored-replace rules for directories several sessions write to.

The full procedure, the boundaries and where the rules came from are in [SKILL.md](SKILL.md).

## Install

Copy the folder into your skills directory (the skill is the repository root):

```bash
git clone https://github.com/NickkkLian/nk-memory-with-conditions ~/.claude/skills/nk-memory-with-conditions
```

or inside one project: `git clone … .claude/skills/nk-memory-with-conditions`.

As a plugin, through the marketplace in the index repository:

```
/plugin marketplace add NickkkLian/nickkk-skills
/plugin install nk-memory-with-conditions@nickkk-skills
```

To try it for one session without installing: `claude --plugin-dir ./nk-memory-with-conditions`.

## Verify

```bash
python3 scripts/memguard.py --selftest
```

Standard library only, Python 3.9+. Before publishing, the guarded lines of each script were
mutated one at a time in a sandbox copy and the self-test was confirmed to go red on the named
assertion, without a traceback; the unmutated control stayed green.

## License

MIT. Read a script before letting it run in your environment.
