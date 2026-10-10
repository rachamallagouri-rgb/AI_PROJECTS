"""No-dependency Windows-friendly Tkinter simulator interface."""
from __future__ import annotations

from .controller import SafetyController
from .models import Action, InputError, Observation, observation_from_dict
from .scenarios import load_scenarios


def launch_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("Tkinter is unavailable. Run 'python -m mforce demo' for a console demonstration.")
        return 1

    try:
        root = tk.Tk()
    except tk.TclError:
        print("No graphical display is available. Run 'python -m mforce demo' instead.")
        return 1
    root.title("MForce | Vehicle Safety Simulator v0.1")
    root.geometry("925x710")
    root.minsize(840, 620)
    root.configure(bg="#0B1221")
    scenarios = load_scenarios()
    by_title = {s["title"]: s for s in scenarios}
    controller = SafetyController()
    cursor = 0
    current: Observation | None = None
    running_job: str | None = None
    bg, panel, accent, text = "#0B1221", "#142138", "#66D9EF", "#F2F5FA"

    tk.Label(root, text="MFORCE  /  AUTOMATION LAB", bg=bg, fg=accent,
             font=("Segoe UI", 21, "bold")).pack(anchor="w", padx=20, pady=(14, 0))
    tk.Label(root, text="Rule-based safety logic | simulated sensors only | NO HARDWARE OUTPUT",
             bg=bg, fg="#B6C2D7", font=("Segoe UI", 10)).pack(anchor="w", padx=22, pady=(0, 10))
    controls = tk.Frame(root, bg=bg)
    controls.pack(fill="x", padx=18)
    scenario_name = tk.StringVar(value=scenarios[0]["title"])
    picker = ttk.Combobox(controls, textvariable=scenario_name, values=list(by_title), width=49, state="readonly")
    picker.pack(side="left", padx=(2, 12))
    status = tk.StringVar(value="Select a scenario and click Next frame.")

    canvas = tk.Canvas(root, bg=panel, highlightthickness=0, height=390)
    canvas.pack(fill="both", expand=True, padx=20, pady=12)
    tk.Label(root, textvariable=status, bg=bg, fg=text, anchor="w",
             font=("Segoe UI", 11, "bold")).pack(fill="x", padx=22, pady=(0, 6))
    events = tk.Text(root, bg="#0F1A2C", fg="#DAE6F6", insertbackground=text,
                     height=7, font=("Consolas", 10), relief="flat", state="disabled")
    events.pack(fill="x", padx=20, pady=(0, 12))

    def write_event(message: str) -> None:
        events.configure(state="normal")
        events.insert("end", message + "\n")
        events.see("end")
        events.configure(state="disabled")

    def draw(observation: Observation | None, action: Action | None) -> None:
        canvas.delete("all")
        w = max(canvas.winfo_width(), 780)
        h = max(canvas.winfo_height(), 360)
        x0, x1 = 95, w - 95
        width = x1 - x0
        lane_x = {"left": x0 + width / 6, "center": x0 + width / 2, "right": x0 + 5 * width / 6}
        canvas.create_rectangle(x0, 15, x1, h - 15, fill="#243047", outline="#526580", width=2)
        for mult in (1, 2):
            x = x0 + width * mult / 3
            canvas.create_line(x, 16, x, h - 15, fill="#AAB9CC", width=2, dash=(14, 12))
        for lane, cx in lane_x.items():
            canvas.create_text(cx, 33, text=lane.upper(), fill="#DCE8F8", font=("Segoe UI", 10, "bold"))
        if observation and observation.obstacle:
            cx = lane_x["center"]
            canvas.create_rectangle(cx - 35, 80, cx + 35, 153, fill="#E56868", outline="#FFD0D0", width=2)
            canvas.create_text(cx, 100, text="TRUCK" if observation.obstacle.category == "six_wheeler" else "OBJECT", fill="white", font=("Segoe UI", 9, "bold"))
            canvas.create_text(cx, 128, text=f"{observation.obstacle.distance_m:g} m", fill="white", font=("Segoe UI", 10))
        cx = lane_x[controller.current_lane]
        canvas.create_rectangle(cx - 24, h - 140, cx + 24, h - 58, fill="#42B7E9", outline="#B8EAFD", width=3)
        canvas.create_text(cx, h - 98, text="EV", fill="#03243A", font=("Segoe UI", 12, "bold"))
        canvas.create_text(18, h / 2, text="SIM", fill=accent, font=("Segoe UI", 13, "bold"), angle=90)
        if action:
            selected = "#7BE4AE" if action in (Action.CRUISE, Action.CHANGE_LEFT, Action.CHANGE_RIGHT) else "#F0BF74"
            canvas.create_text(w / 2, h - 26, text=f"DECISION: {action.value}", fill=selected, font=("Segoe UI", 14, "bold"))

    def reset() -> None:
        nonlocal cursor, current, running_job
        if running_job is not None:
            root.after_cancel(running_job)
            running_job = None
        controller.reset()
        cursor = 0
        current = None
        status.set(f"Ready: {scenario_name.get()} | Frame 0")
        events.configure(state="normal")
        events.delete("1.0", "end")
        events.configure(state="disabled")
        draw(None, None)

    def step() -> None:
        nonlocal cursor, current
        scenario = by_title[scenario_name.get()]
        if cursor >= len(scenario["frames"]):
            status.set(f"Completed {cursor} frames. Select Reset to repeat.")
            return
        try:
            current = observation_from_dict(scenario["frames"][cursor])
            decision = controller.decide(current)
        except InputError as exc:
            status.set(f"Sensor input rejected: {exc}")
            write_event(f"INPUT REJECTED: {exc}")
            return
        cursor += 1
        status.set(f"Frame {cursor}/{len(scenario['frames'])} | {decision.action.value} | Lane: {decision.selected_lane}")
        write_event(f"[{cursor:02}] {decision.action.value:17} | {decision.reason} | safe frames: L={decision.left_safe_frames}, R={decision.right_safe_frames}")
        draw(current, decision.action)

    def run_all() -> None:
        nonlocal running_job
        step()
        if cursor < len(by_title[scenario_name.get()]["frames"]):
            running_job = root.after(650, run_all)
        else:
            running_job = None

    def close() -> None:
        nonlocal running_job
        if running_job is not None:
            root.after_cancel(running_job)
            running_job = None
        root.destroy()

    ttk.Button(controls, text="Next frame", command=step).pack(side="left", padx=5)
    ttk.Button(controls, text="Run", command=run_all).pack(side="left", padx=5)
    ttk.Button(controls, text="Reset", command=reset).pack(side="left", padx=5)
    picker.bind("<<ComboboxSelected>>", lambda _: reset())
    canvas.bind("<Configure>", lambda _: draw(current, None))
    root.protocol("WM_DELETE_WINDOW", close)
    reset()
    root.mainloop()
    return 0
