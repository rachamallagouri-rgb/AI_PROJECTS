# RAM AI CCTV — Intelligent Surveillance Prototype

A lightweight, GitHub-ready AI CCTV prototype for event-aware surveillance, camera health monitoring, evidence logging, natural-language event queries, optional object detection, known/unknown face recognition readiness, and RAM AI app integration.

> This repository intentionally excludes trained model weights, recordings, datasets, virtual environments, secrets, and generated evidence files so the repository stays small and safe for GitHub.

## Key Features

- Webcam, video file, or RTSP camera input
- Multi-camera support
- Motion and person detection
- Optional YOLO object detection
- Face enrollment and known/unknown recognition readiness
- Event-based recording with pre/post-event buffering
- Camera health checks: blur, darkness, frozen feed, read failures, FPS, and disk space
- SQLite event memory
- SHA-256 evidence capsule generation
- Conservative possible-object-removal review
- Natural-language-style CCTV queries
- Optional voice input/output
- Telegram/webhook alert hooks
- REST API + MJPEG stream for RAM AI app integration
- User feedback with bounded sensitivity adjustment
- Local-first design

## Quick Start — Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python .\src\ram_ai_cctv.py --doctor
python .\src\ram_ai_cctv.py --self-test
python .\src\ram_ai_cctv.py --source 0
```

Optional YOLO:

```powershell
python -m pip install -r requirements-optional.txt
python .\src\ram_ai_cctv.py --source 0 --enable-yolo
```

## Example AI Commands

```text
status
camera health
what happened recently?
who came?
unknown
event 1
open 1
enroll Alice
feedback 1 useful
```

## RAM AI App Integration

For LAN access, set an API key first:

```powershell
$env:RAM_AI_API_KEY="replace-with-a-long-random-key"
python .\src\ram_ai_cctv.py --source 0 --bind 0.0.0.0 --port 8765
```

Example endpoints:

```text
GET  /api/status
GET  /api/health
GET  /api/events
GET  /api/event/<id>
POST /api/query
POST /api/feedback
GET  /stream/cam1.mjpg
```

## Important Notes

- Prototype, not a certified commercial security system.
- AI detections can be wrong.
- “Unknown” does not mean suspicious or criminal.
- Possible object removal is a review signal, not a theft determination.
- Never commit camera passwords, API keys, private face datasets, recordings, or personal data.

## Resume Summary

**RAM AI CCTV — AI-Powered Intelligent Surveillance Prototype**  
Built a local-first AI CCTV prototype using Python, OpenCV, SQLite, optional YOLO, REST APIs, event-based recording, camera self-health monitoring, evidence hashing, natural-language event queries, and app-integration endpoints.

## Tech Stack

Python · OpenCV · NumPy · SQLite · REST API · Computer Vision · Optional YOLO · SHA-256 · Edge AI

## License

MIT License. See `LICENSE`.
