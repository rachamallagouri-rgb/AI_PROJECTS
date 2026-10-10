"""Input validation and output types for simulation-only vehicle decisions."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any


class InputError(ValueError):
    """Raised if a sensor record is missing, malformed, or out of range."""


class Action(str, Enum):
    CRUISE = "CRUISE"
    WAIT_STOP = "WAIT_STOP"
    CHANGE_LEFT = "CHANGE_LEFT"
    CHANGE_RIGHT = "CHANGE_RIGHT"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    FAULT_STOP = "FAULT_STOP"


@dataclass(frozen=True)
class Obstacle:
    category: str
    distance_m: float
    confidence: float


@dataclass(frozen=True)
class LaneStatus:
    clear: bool
    approved: bool
    clearance_m: float
    oncoming: bool
    confidence: float


@dataclass(frozen=True)
class Observation:
    event_time_s: float
    sensor_time_s: float
    ego_speed_mps: float
    sensor_ok: bool
    emergency_stop: bool
    obstacle: Obstacle | None
    left: LaneStatus
    right: LaneStatus


@dataclass(frozen=True)
class Decision:
    action: Action
    target_speed_mps: float
    selected_lane: str
    reason: str
    left_safe_frames: int = 0
    right_safe_frames: int = 0


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError(f"{name} must be a JSON object")
    return value


def _boolean(data: dict[str, Any], key: str, context: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise InputError(f"{context}.{key} must be true or false")
    return value


def _number(data: dict[str, Any], key: str, context: str, *, minimum: float = 0.0, maximum: float | None = None) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise InputError(f"{context}.{key} must be a finite number")
    result = float(value)
    if result < minimum or (maximum is not None and result > maximum):
        raise InputError(f"{context}.{key} is outside the valid range")
    return result


def _lane_status(raw: Any, side: str) -> LaneStatus:
    data = _object(raw, f"lanes.{side}")
    return LaneStatus(
        clear=_boolean(data, "clear", side),
        approved=_boolean(data, "approved", side),
        clearance_m=_number(data, "clearance_m", side),
        oncoming=_boolean(data, "oncoming", side),
        confidence=_number(data, "confidence", side, maximum=1.0),
    )


def observation_from_dict(raw: Any) -> Observation:
    """Parse a sensor record. Never silently assume missing information is safe."""
    data = _object(raw, "observation")
    lanes = _object(data.get("lanes"), "lanes")
    raw_obstacle = data.get("obstacle")
    obstacle: Obstacle | None = None
    if raw_obstacle is not None:
        obj = _object(raw_obstacle, "obstacle")
        category = obj.get("category")
        if not isinstance(category, str) or not category.strip():
            raise InputError("obstacle.category must be a nonempty string")
        obstacle = Obstacle(
            category=category.strip(),
            distance_m=_number(obj, "distance_m", "obstacle"),
            confidence=_number(obj, "confidence", "obstacle", maximum=1.0),
        )
    return Observation(
        event_time_s=_number(data, "event_time_s", "observation"),
        sensor_time_s=_number(data, "sensor_time_s", "observation"),
        ego_speed_mps=_number(data, "ego_speed_mps", "observation"),
        sensor_ok=_boolean(data, "sensor_ok", "observation"),
        emergency_stop=_boolean(data, "emergency_stop", "observation"),
        obstacle=obstacle,
        left=_lane_status(lanes.get("left"), "left"),
        right=_lane_status(lanes.get("right"), "right"),
    )
