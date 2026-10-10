"""Run every version-controlled scenario and check its expected output."""
import unittest
from pathlib import Path

from mforce import __version__
from mforce.scenarios import SCENARIO_DIR, load_scenarios, run_scenario


class ScenarioTests(unittest.TestCase):
    def test_all_expected_actions(self):
        for scenario in load_scenarios():
            with self.subTest(scenario=scenario['id']):
                self.assertEqual([d.action.value for d in run_scenario(scenario)], scenario['expected_actions'])

    def test_scenario_ids_are_unique(self):
        values = [s['id'] for s in load_scenarios()]
        self.assertEqual(len(values), len(set(values)))

    def test_scenarios_present(self):
        self.assertGreaterEqual(len(list(SCENARIO_DIR.glob('*.json'))), 10)

    def test_version(self):
        self.assertEqual(__version__, '0.1.0')


if __name__ == '__main__':
    unittest.main()
