# RAM AI — Android + AI Backend

This package contains:
- `android_app/`: Native Android Studio RAM AI application.
- `backend/`: FastAPI service for authentication, assistant routing, and real PyTorch model inference.

Implemented product surfaces:
- RAM AI login/account shell
- Voice input + text-to-speech response
- AI chat/orchestrator endpoint
- NeuroSpec MRI
- NeuroSpec CT
- Audio AI
- CCTV AI
- Defensive Cyber AI
- Smart Glasses integration entry point

## Important distinction
The Android application is fully wired to call real inference endpoints. Actual learned behavior comes from your trained model files. The package does not fabricate missing model weights or architecture code.

## Recommended deployment sequence
1. Run backend locally.
2. Build Android debug APK and test all endpoints.
3. Export and connect each trained model one by one.
4. Move backend to an HTTPS GPU/server environment.
5. Build signed Android App Bundle (AAB).
6. Complete Google Play privacy/data-safety/content-rating declarations and release testing.
