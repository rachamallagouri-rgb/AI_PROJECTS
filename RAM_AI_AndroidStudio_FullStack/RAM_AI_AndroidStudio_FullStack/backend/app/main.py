from __future__ import annotations

import os
import sqlite3
from typing import List

import httpx
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field

from .db import connect, init_db
from .model_registry import registry
from .security import create_token, hash_password, verify_password, verify_token

app = FastAPI(title="RAM AI Backend", version="0.1.0")


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


class CyberRequest(BaseModel):
    features: List[float] = Field(min_length=1, max_length=1000)


@app.on_event("startup")
def startup():
    init_db()


def current_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    subject = verify_token(authorization.removeprefix("Bearer ").strip())
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE email=?", (subject,)).fetchone()
    if not exists:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return subject


@app.get("/health")
def health():
    return {"ok": True, "service": "RAM AI", "models": registry.status()}


@app.post("/v1/auth/register")
def register(req: AuthRequest):
    email = req.email.lower()
    try:
        with connect() as conn:
            conn.execute("INSERT INTO users(email, password_hash) VALUES (?, ?)", (email, hash_password(req.password)))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Account already exists")
    return {"access_token": create_token(email), "token_type": "bearer"}


@app.post("/v1/auth/login")
def login(req: AuthRequest):
    email = req.email.lower()
    with connect() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE email=?", (email,)).fetchone()
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_token(email), "token_type": "bearer"}


@app.delete("/v1/account")
def delete_account(user: str = Depends(current_user)):
    with connect() as conn:
        conn.execute("DELETE FROM users WHERE email=?", (user,))
    return {"deleted": True}


@app.get("/account-deletion", response_class=HTMLResponse)
def account_deletion_page():
    return """
    <!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>Delete RAM AI account</title></head>
    <body style='font-family:system-ui;max-width:520px;margin:40px auto;padding:20px'>
    <h1>Delete RAM AI account</h1>
    <p>Enter your RAM AI account credentials to permanently delete the account stored by this service.</p>
    <form method='post' action='/account-deletion'>
      <label>Email</label><br><input name='email' type='email' required style='width:100%;padding:10px'><br><br>
      <label>Password</label><br><input name='password' type='password' minlength='8' required style='width:100%;padding:10px'><br><br>
      <button type='submit' style='padding:12px 18px'>Delete account permanently</button>
    </form></body></html>
    """


@app.post("/account-deletion", response_class=HTMLResponse)
def account_deletion_submit(email: str = Form(...), password: str = Form(...)):
    normalized = email.strip().lower()
    with connect() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE email=?", (normalized,)).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return HTMLResponse("<h2>Account not found or password incorrect.</h2><p>No data was deleted.</p>", status_code=401)
        conn.execute("DELETE FROM users WHERE email=?", (normalized,))
    return HTMLResponse("<h2>RAM AI account deleted.</h2><p>The account record has been permanently removed.</p>")


@app.get("/v1/models/status")
def models_status(_: str = Depends(current_user)):
    return registry.status()


@app.post("/v1/chat")
async def chat(req: ChatRequest, _: str = Depends(current_user)):
    ollama_url = os.getenv("RAM_OLLAMA_URL", "").rstrip("/")
    ollama_model = os.getenv("RAM_OLLAMA_MODEL", "")
    if ollama_url and ollama_model:
        payload = {
            "model": ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": "You are RAM AI. Be concise, safe, and route users to MRI, CT, audio, CCTV, cyber-defense, or smart-glasses features when relevant."},
                {"role": "user", "content": req.message},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                r = await client.post(f"{ollama_url}/api/chat", json=payload)
                r.raise_for_status()
                answer = r.json()["message"]["content"]
                return {"answer": answer, "provider": "ollama"}
        except Exception as exc:
            return {"answer": f"The local language model is configured but unavailable: {exc}", "provider": "fallback"}

    lower = req.message.lower()
    if any(k in lower for k in ("mri", "brain", "scan")):
        answer = "Open NeuroSpec MRI to select an MRI input and run your configured MRI model."
    elif "ct" in lower:
        answer = "Open NeuroSpec CT to run the configured CT model on a supported input."
    elif any(k in lower for k in ("cctv", "camera", "theft")):
        answer = "Open CCTV AI to analyze an image or camera frame with the configured vision model."
    elif any(k in lower for k in ("cyber", "network", "intrusion")):
        answer = "Open Cyber Defense and provide the numeric feature vector expected by your defensive intrusion-detection model."
    else:
        answer = "RAM AI backend is connected. Configure RAM_OLLAMA_URL/RAM_OLLAMA_MODEL for a local language model, and place your exported TorchScript project models in the backend models folders."
    return {"answer": answer, "provider": "router"}


async def infer_upload(feature: str, file: UploadFile):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty upload")
    try:
        result = registry.infer_file(feature, content, file.filename or "input.bin")
        result["filename"] = file.filename
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Inference failed: {exc}")


@app.post("/v1/mri/analyze")
async def mri(file: UploadFile = File(...), _: str = Depends(current_user)):
    return await infer_upload("mri", file)


@app.post("/v1/ct/analyze")
async def ct(file: UploadFile = File(...), _: str = Depends(current_user)):
    return await infer_upload("ct", file)


@app.post("/v1/audio/analyze")
async def audio(file: UploadFile = File(...), _: str = Depends(current_user)):
    return await infer_upload("audio", file)


@app.post("/v1/cctv/analyze")
async def cctv(file: UploadFile = File(...), _: str = Depends(current_user)):
    return await infer_upload("cctv", file)


@app.post("/v1/cyber/analyze")
def cyber(req: CyberRequest, _: str = Depends(current_user)):
    try:
        return registry.infer_features("cyber", req.features)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Inference failed: {exc}")
