# Resume and portfolio guidance

## Recommended project entry

**MForce — Vehicle Safety Automation Simulator**  
*Python, finite-state machine, object-oriented programming, Tkinter, JSON, unittest, GitHub Actions*

- Built a desktop-based simulation of vehicle obstacle-response logic, including a six-wheeler detection scenario and conditional left/right path selection.
- Implemented fail-closed decisions for uncertain obstacles, stale sensor input, invalid side paths, emergency stops, and health faults.
- Designed reusable Python modules for input validation, safety state transitions, automated tests, interactive visualization, and CSV scenario reports.
- Integrated GitHub Actions for repeatable automated testing on code pushes and pull requests.

## Interview demo script (2–3 minutes)

1. Explain the goal: *show conservative decision-making from simulated sensor data*.
2. Open `START_MFORCE.bat`, choose **Truck ahead - safe left path**, and click **Next frame** repeatedly. Show `WAIT_STOP → WAIT_STOP → CHANGE_LEFT → CRUISE`.
3. Choose **Truck ahead - both paths blocked**. Show repeated `WAIT_STOP` instead of a forced change.
4. Choose **Camera / sensor failure** and **Emergency stop latch**. Show the latched results.
5. Show `tests/`, the GitHub Actions test run, and `output/demo_results.csv`.

## What to say accurately

- "I implemented a rule-based, simulation-only vehicle safety controller."
- "I validated deterministic behavior with regression tests and scenario data."
- "The architecture can later connect to perception/robotics simulators, but no real vehicle or trained AI model is integrated yet."

Avoid claiming **full self-driving AI**, **real-time vehicle safety**, **trained ML accuracy**, **hardware integration**, or **zero errors**. These claims require actual implementation and evidence.

## Suggested repository topics

`python`, `automation`, `vehicle-simulation`, `state-machine`, `autonomous-vehicles`, `software-testing`, `tkinter`, `github-actions`

The working source, readable README, reproducible tests, and honest limitations make this a defensible student project for AI/ML software and automation internship applications.
