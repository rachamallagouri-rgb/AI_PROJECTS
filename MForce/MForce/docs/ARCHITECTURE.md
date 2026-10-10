# Architecture and engineering choices

**Scope:** reproducible software-in-the-loop *toy simulation*, not real-time vehicle control.

## Software components

| Component | File | Function |
|---|---|---|
| Input schema | `mforce/models.py` | Reject missing, nonfinite, negative, and untrusted sensor fields |
| Safety state machine | `mforce/controller.py` | Produce deterministic abstract decisions from valid input |
| Scenarios | `mforce/scenarios.py` | Load version-controlled inputs and expected actions |
| Visualization | `mforce/gui.py` | Render a simplified three-lane scene and decision trace |
| Test runner | `python -m mforce test` | Run standard-library automated tests |
| Reports | `python -m mforce demo` | Export CSV to `output/demo_results.csv` |

## Sensor data contract

Each JSON frame contains: event time, sensor sample time, ego speed, sensor health, emergency stop flag, zero or one obstacle (class, distance, confidence), and left/right lane assessments (clearance, approval, oncoming traffic, confidence). Each field is mandatory except an obstacle can explicitly be `null`. Missing or invalid fields are rejected.

The abstract lane `approved` flag is already provided by each simulated scenario. **MForce does not calculate lawful passing or road geometry.** In real driving that would be a large separate problem.

## Critical controller policies

1. An emergency stop takes priority and is latched until a manual simulator reset.
2. Any unhealthy, stale, future-dated, or replayed sensor record causes a latched fault-stop.
3. Nearby low-confidence obstacles force waiting, not a guessed lane change.
4. Detecting a high-confidence nearby obstacle while ego speed exceeds the stop threshold returns a stop decision.
5. Only stationary simulated frames can contribute to lane stability counts.
6. Each side path requires approval, sufficient clearance, high confidence, no oncoming traffic, and multiple **consecutive** qualifying frames.
7. This baseline allows one lateral choice from the center only, preventing repeated side-to-side evasive changes.
8. When no eligible path is validated, return a zero-speed `WAIT_STOP` abstract request.

The outputs are *data records*, not actuator control, and no physical braking distances, control stability, traffic-law compliance, or collision prediction are modeled.

## Testing strategy

- Unit tests validate transitions, stale and future sensor records, emergency/fault latching, and input validation.
- Scenario tests run all packaged cases against version-controlled expected actions.
- CLI test verifies that the demo creates a CSV report.
- CI reruns tests on pushes/PRs. A passing test run proves only that the software matches **these test expectations**, not that a vehicle would be safe.

## Extension boundaries

A later sensor adapter should provide validated `Observation` objects; it must not directly energize motors from controller actions. Real robotics requires independent emergency-stop hardware, redundant sensing, geometry, time synchronization, fail-safe motion control, and engineering approval; it cannot be achieved simply by plugging this Python code into a motor driver.
