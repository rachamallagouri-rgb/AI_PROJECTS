# Local verification log — MForce v0.1.0

Environment used for the initial build: Python 3.13.5 (Linux test runner).

Checks completed:

- Python syntax compilation for `mforce` and `tests`: **passed**.
- `python -m unittest discover -s tests -v`: **25/25 tests passed**.
- `python -m mforce demo`: **12/12 scripted scenarios passed**.
- Tkinter GUI smoke check under a virtual X display: **passed** (launch, Next frame, Reset, Run).
- Source ZIP extracted into a folder whose name includes spaces; test/demo commands: **passed**.

Tests demonstrate correctness of the checked behavior in this environment only. A clean Windows/Python installation and GitHub-hosted CI still need to be run by the project owner. Do not treat these checks as a road-safety certification.

`evidence/sample_demo_results.csv` is a snapshot of the passing simulated scenario output, not real sensor or road data.
