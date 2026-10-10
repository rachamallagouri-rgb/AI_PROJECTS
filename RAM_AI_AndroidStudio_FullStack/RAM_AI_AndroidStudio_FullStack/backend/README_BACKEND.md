# RAM AI Backend

This backend is the AI execution layer for the Android app.

## Why backend inference?
MRI, CT, CCTV and other PyTorch models can be large and GPU-dependent. Keeping them server-side avoids a huge APK and makes model updates possible without publishing a new Android build.

## Start
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Install the PyTorch package appropriate to your server/GPU.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://127.0.0.1:8000/docs` for the API tester.

## Real model integration
The model registry loads TorchScript `.pt` files. Your existing `.pth` files must be loaded using their original architecture class and exported to TorchScript first. This is deliberate: guessing an architecture from weights is unsafe and usually fails.

Expected files:
- `models/mri/final_mri_model.pt`
- `models/ct/final_ct_model.pt`
- `models/audio/final_audio_model.pt`
- `models/cctv/final_cctv_model.pt`
- `models/cyber/final_cyber_model.pt`

Then adjust `_file_to_tensor()` in `app/model_registry.py` to match the exact preprocessing used during training.

## Production
- Use HTTPS.
- Set a strong `RAM_TOKEN_SECRET`.
- Put the backend behind a reverse proxy/load balancer.
- Store medical/user uploads only with explicit consent and retention rules.
- Do not claim clinical diagnosis unless your product has the required validation/regulatory approvals.

## Account deletion
The backend includes both:
- authenticated in-app deletion: `DELETE /v1/account`
- external deletion page: `/account-deletion`

Host the external page on your production HTTPS domain and enter its URL in Play Console.
