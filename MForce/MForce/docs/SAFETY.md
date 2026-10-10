# Safety and limitations

MForce is a **software-only educational demonstration**. Treat all lane positions, distances, clearances, and speed targets as illustrative toy values. The `CHANGE_LEFT` / `CHANGE_RIGHT` labels represent hypothetical intentions, **not valid autonomous driving maneuvers**.

**Do not** connect these outputs to steering, propulsion, braking, drones, robots carrying loads, industrial machinery, or public-road vehicles. The project does not have production-grade perception, braking physics, safe trajectory planning, lane marking detection, object tracking, road regulations, speed-limit handling, safety cases, redundancy, functional safety certification, or physical validation. It is not a medical or safety-critical system.

Real-world passing decisions cannot be made safely from an "empty left/right" Boolean. An apparently free path may contain fast oncoming traffic, motorcycles, pedestrians, road boundaries, blind spots, or insufficient maneuver distance. In actual vehicle engineering, the safest response to uncertainty is generally to minimize risk and use validated emergency procedures — not improvise a swerve.

A stopped vehicle may still be in danger from an approaching truck; this simulator does **not** model relative speeds or collision dynamics. Its script demonstrates a decision *concept* rather than a road-safe response.

Confidence numbers supplied in JSON are **synthetic inputs**; no ML perception performance or false-negative risk has been measured.

A GitHub Actions green check or a successful local test suite cannot guarantee absence of errors, cybersecurity weaknesses, or physically unsafe behavior. It verifies only the tested software behavior in specific environments.

Magnetic motors/generators obey conservation of energy: permanent magnets and self-rotation are not a sustainable standalone energy source. A real electric vehicle must receive energy from a battery, fuel, an external supply, or another physical source.
