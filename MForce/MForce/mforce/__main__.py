"""Run `python -m mforce` (GUI), `demo`, `test`, or `version`."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
import unittest

from . import __version__
from .models import InputError
from .scenarios import load_scenarios, run_scenario


def run_demo() -> int:
    scenarios = load_scenarios()
    records: list[dict[str, object]] = []
    failures = 0
    for scenario in scenarios:
        actions = [item.action.value for item in run_scenario(scenario)]
        passed = actions == scenario["expected_actions"]
        failures += not passed
        print(f"{'PASS' if passed else 'FAIL'}  {scenario['title']} -> {' / '.join(actions)}")
        for i, action in enumerate(actions):
            records.append({"scenario": scenario["id"], "frame": i + 1, "action": action, "expected": scenario["expected_actions"][i], "passed": action == scenario["expected_actions"][i]})
    out_dir = Path(__file__).resolve().parents[1] / "output"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "demo_results.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["scenario", "frame", "action", "expected", "passed"])
        writer.writeheader()
        writer.writerows(records)
    print(f"\n{len(scenarios) - failures}/{len(scenarios)} scenarios passed. Results: {path}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MForce software-only vehicle automation simulator")
    parser.add_argument("mode", nargs="?", choices=("gui", "demo", "test", "version"), default="gui")
    args = parser.parse_args(argv)
    try:
        if args.mode == "demo":
            return run_demo()
        if args.mode == "version":
            print(f"MForce {__version__}")
            return 0
        if args.mode == "test":
            project_root = Path(__file__).resolve().parents[1]
            suite = unittest.defaultTestLoader.discover(str(project_root / "tests"), top_level_dir=str(project_root))
            return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
        from .gui import launch_gui
        return launch_gui()
    except (InputError, OSError) as exc:
        print(f"MForce error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
