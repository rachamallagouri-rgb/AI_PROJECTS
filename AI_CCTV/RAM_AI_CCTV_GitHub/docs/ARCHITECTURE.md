# Architecture

```text
Camera / RTSP / Video
        |
        v
Frame Capture
        |
        +--> Motion Detection
        +--> Person / Object Detection
        +--> Face Detection / Recognition Readiness
        |
        v
Event Decision Engine
        |
        +--> Event Recording
        +--> SQLite Event Memory
        +--> Evidence SHA-256 Capsule
        +--> Camera Health Monitoring
        +--> Alerts
        |
        v
Query Engine + REST API + MJPEG Stream
        |
        v
RAM AI Mobile / Web App
```

Design principles: local-first processing, evidence-grounded answers, privacy-aware identity handling, bounded feedback tuning, and keeping runtime data out of Git.
