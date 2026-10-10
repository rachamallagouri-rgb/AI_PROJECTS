"""Reproducible simulation inputs stored as human-readable JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controller import SafetyController
from .models import Decision, InputError, observation_from_dict

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "data" / "scenarios"


def load_scenarios() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    paths = sorted(SCENARIO_DIR.glob("*.json"))
    if not paths:
        raise InputError(f"No scenario JSON files found in {SCENARIO_DIR}")
    for path in paths:
        try:
            scenario = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputError(f"Unable to read {path.name}: {exc}") from exc
        if not isinstance(scenario, dict) or not all(k in scenario for k in ("id", "title", "frames", "expected_actions")):
            raise InputError(f"{path.name}: missing scenario metadata")
        if not isinstance(scenario["id"], str) or not isinstance(scenario["title"], str):
            raise InputError(f"{path.name}: scenario id/title must be text")
        if not isinstance(scenario["frames"], list) or not scenario["frames"]:
            raise InputError(f"{path.name}: frames must be a nonempty list")
        if not isinstance(scenario["expected_actions"], list) or len(scenario["frames"]) != len(scenario["expected_actions"]):
            raise InputError(f"{path.name}: expected_actions count must match frames")
        for frame in scenario["frames"]:
            observation_from_dict(frame)
        results.append(scenario)
    return results


def run_scenario(scenario: dict[str, Any]) -> list[Decision]:
    controller = SafetyController()
    return [controller.decide(observation_from_dict(frame)) for frame in scenario["frames"]]
