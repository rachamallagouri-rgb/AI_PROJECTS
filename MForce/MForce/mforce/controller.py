"""Fail-closed, rule-based simulation controller (NOT for real vehicles)."""
from __future__ import annotations

from dataclasses import dataclass
from .models import Action, Decision, LaneStatus, Observation


@dataclass(frozen=True)
class SafetyConfig:
    hazard_distance_m: float = 25.0
    min_lane_clearance_m: float = 25.0
    min_confidence: float = 0.85
    max_sensor_age_s: float = 0.5
    stop_speed_threshold_mps: float = 0.05
    required_stable_frames: int = 2
    demo_cruise_speed_mps: float = 2.0
    demo_change_speed_mps: float = 0.5


class SafetyController:
    """Decision state machine for scripted scenarios, with no hardware interface."""

    def __init__(self, config: SafetyConfig | None = None) -> None:
        self.config = config if config is not None else SafetyConfig()
        self.reset()

    def reset(self) -> None:
        """Explicit simulator reset is required after any latched fault or E-stop."""
        self.current_lane = "center"
        self._left_count = 0
        self._right_count = 0
        self._last_time: float | None = None
        self._emergency_latched = False
        self._fault_latched = False

    def _decision(self, action: Action, speed: float, reason: str) -> Decision:
        return Decision(action, speed, self.current_lane, reason, self._left_count, self._right_count)

    def _is_lane_safe(self, lane: LaneStatus) -> bool:
        c = self.config
        return (
            lane.clear
            and lane.approved
            and not lane.oncoming
            and lane.clearance_m >= c.min_lane_clearance_m
            and lane.confidence >= c.min_confidence
        )

    def decide(self, obs: Observation) -> Decision:
        c = self.config
        if obs.emergency_stop:
            self._emergency_latched = True
        if self._emergency_latched:
            return self._decision(Action.EMERGENCY_STOP, 0.0, "Emergency stop is latched; simulator reset required")
        if self._fault_latched:
            return self._decision(Action.FAULT_STOP, 0.0, "Sensor fault is latched; simulator reset required")

        invalid_timing = (
            obs.sensor_time_s > obs.event_time_s
            or obs.event_time_s - obs.sensor_time_s > c.max_sensor_age_s
            or (self._last_time is not None and obs.event_time_s <= self._last_time)
        )
        if not obs.sensor_ok or invalid_timing:
            self._fault_latched = True
            self._left_count = self._right_count = 0
            return self._decision(Action.FAULT_STOP, 0.0, "Unhealthy, stale, future-dated, or repeated sensor sample")
        self._last_time = obs.event_time_s

        if obs.obstacle is None or obs.obstacle.distance_m > c.hazard_distance_m:
            self._left_count = self._right_count = 0
            return self._decision(Action.CRUISE, c.demo_cruise_speed_mps, "No hazard within simulated detection range")

        # A low-confidence object can never be treated as a clear road.
        if obs.obstacle.confidence < c.min_confidence:
            self._left_count = self._right_count = 0
            return self._decision(Action.WAIT_STOP, 0.0, "Uncertain nearby obstacle: stop and verify")

        # Even an otherwise clear alternate lane cannot be chosen while moving.
        if obs.ego_speed_mps > c.stop_speed_threshold_mps:
            self._left_count = self._right_count = 0
            return self._decision(Action.WAIT_STOP, 0.0, f"Nearby {obs.obstacle.category}: stop before evaluating an alternate path")

        # This prototype only changes away from the center lane. No repeated evasive swerving.
        if self.current_lane != "center":
            self._left_count = self._right_count = 0
            return self._decision(Action.WAIT_STOP, 0.0, "Hazard still present after lane change: remain stopped")

        self._left_count = self._left_count + 1 if self._is_lane_safe(obs.left) else 0
        self._right_count = self._right_count + 1 if self._is_lane_safe(obs.right) else 0
        if self._left_count >= c.required_stable_frames:
            self.current_lane = "left"
            return self._decision(Action.CHANGE_LEFT, c.demo_change_speed_mps, "Left simulation path verified over consecutive sensor frames")
        if self._right_count >= c.required_stable_frames:
            self.current_lane = "right"
            return self._decision(Action.CHANGE_RIGHT, c.demo_change_speed_mps, "Right simulation path verified over consecutive sensor frames")
        return self._decision(Action.WAIT_STOP, 0.0, "No verified alternate path: wait at zero requested speed")
