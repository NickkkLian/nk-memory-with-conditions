# Writing to a memory directory that other sessions may be writing too

The dangerous shape is read-all → modify → write-all. Between your read and your write, another session's
append is lost; nothing errors; the line count still looks right, because you wrote back "what I read plus
my change".

| Operation | Do it as |
|---|---|
| add a memory | create the file; **append** one line to `MEMORY.md` (`open(p, "a")`, `>>`) |
| edit a memory line | anchored replace: read, `assert text.count(old) == 1`, replace, write; if the assert fails, stop |
| unavoidable full rewrite | compare-and-swap: hash the file at start, re-read just before writing, abort if the hash changed |
| after any write | line count of `MEMORY.md` must not have gone down |
| index near the cap | move the longest index lines' text into their files verbatim; leave one sentence in the index |

`python3 memguard.py --quiet` at session start reports A/B red conditions and nothing else; run it
without `--quiet` to see the shared-directory notice and the counts.
