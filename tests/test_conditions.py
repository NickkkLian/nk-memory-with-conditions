"""Regression for explicit prose conditions and true missing-condition findings."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/memguard.py'
spec = importlib.util.spec_from_file_location('memguard', SCRIPT)
memguard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memguard)


class ConditionsTests(unittest.TestCase):
    def test_prose_is_accepted_without_hiding_four_missing_conditions(self):
        examples = {
            'db-port': 'The database listens on port 5433. This is only true while we are on the old cluster, until migration.',
            'api-location': '**Holds when:** running in the local development sandbox.',
            'deploy': 'Run make ship.',
            'grep-skips': 'The grep command skips files that are ignored.',
            'staging': 'Use staging for release checks.',
            'release-day': 'Releases are on 11-02. Always ask the release owner.',
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, text in examples.items():
                (root / (name + '.md')).write_text(text, encoding='utf-8')
            (root / 'MEMORY.md').write_text(''.join(f'- [{name}]({name}.md)\n' for name in examples), encoding='utf-8')
            rc, lines, facts = memguard.check(str(root), require_conditions=True)
            self.assertEqual(rc, 1)
            self.assertEqual(facts['no_conditions'], 4)
            findings = '\n'.join(line for line in lines if ' D ' in line)
            for name in ('deploy', 'grep-skips', 'staging', 'release-day'):
                self.assertIn(name + '.md', findings)
            self.assertNotIn('db-port.md', findings)
            self.assertNotIn('api-location.md', findings)
            rc, _, facts = memguard.check(str(root))
            self.assertEqual(rc, 0)
            self.assertEqual(facts['no_conditions'], 4)

    def test_examples_do_not_supply_a_condition(self):
        for text in ('```\nHolds when: example\n```', '~~~\nHolds when: example\n~~~', '> Holds when: quoted example'):
            with self.subTest(text=text):
                self.assertFalse(memguard.has_condition(text))


if __name__ == '__main__':
    unittest.main()
