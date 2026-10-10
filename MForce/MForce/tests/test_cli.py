"""Verify the headless reporting path."""
import contextlib
import io
import unittest
from pathlib import Path

from mforce.__main__ import main


class CLITests(unittest.TestCase):
    def test_demo_generates_expected_csv(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['demo']), 0)
        project_root = Path(__file__).resolve().parents[1]
        report = project_root / 'output' / 'demo_results.csv'
        self.assertTrue(report.is_file())
        self.assertIn('scenario,frame,action,expected,passed', report.read_text(encoding='utf-8'))

    def test_version_command(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(['version']), 0)
        self.assertIn('MForce', out.getvalue())


if __name__ == '__main__':
    unittest.main()
