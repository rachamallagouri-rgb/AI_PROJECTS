from __future__ import annotations

import io
import os
import wave
from pathlib import Path
from typing import Any, Dict, Iterable

import numpy as np

try:
    import torch
except Exception:  # keeps /health usable before torch is installed
    torch = None

BASE = Path(__file__).resolve().parents[1]

DEFAULT_MODELS = {
    "mri": BASE / "models/mri/final_mri_model.pt",
    "ct": BASE / "models/ct/final_ct_model.pt",
    "audio": BASE / "models/audio/final_audio_model.pt",
    "cctv": BASE / "models/cctv/final_cctv_model.pt",
    "cyber": BASE / "models/cyber/final_cyber_model.pt",
}

ENV_KEYS = {
    "mri": "RAM_MRI_MODEL",
    "ct": "RAM_CT_MODEL",
    "audio": "RAM_AUDIO_MODEL",
    "cctv": "RAM_CCTV_MODEL",
    "cyber": "RAM_CYBER_MODEL",
}


class ModelRegistry:
    def __init__(self):
        self._models: Dict[str, Any] = {}

    def path_for(self, name: str) -> Path:
        return Path(os.getenv(ENV_KEYS[name], str(DEFAULT_MODELS[name]))).expanduser()

    def status(self) -> Dict[str, dict]:
        out = {}
        for name in DEFAULT_MODELS:
            path = self.path_for(name)
            out[name] = {
                "configured": path.exists(),
                "loaded": name in self._models,
                "path": str(path),
            }
        return out

    def load(self, name: str):
        if torch is None:
            raise RuntimeError("PyTorch is not installed in the backend environment")
        if name in self._models:
            return self._models[name]
        path = self.path_for(name)
        if not path.exists():
            raise FileNotFoundError(
                f"Model not configured: {path}. Export your trained model to TorchScript .pt and place it there."
            )
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = torch.jit.load(str(path), map_location=device)
        model.eval()
        self._models[name] = model
        return model

    def infer_file(self, name: str, content: bytes, filename: str) -> dict:
        tensor = self._file_to_tensor(name, content, filename)
        return self._infer_tensor(name, tensor)

    def infer_features(self, name: str, features: Iterable[float]) -> dict:
        if torch is None:
            raise RuntimeError("PyTorch is not installed")
        x = torch.tensor(list(features), dtype=torch.float32).unsqueeze(0)
        return self._infer_tensor(name, x)

    def _infer_tensor(self, name: str, x):
        model = self.load(name)
        if torch is None:
            raise RuntimeError("PyTorch is not installed")
        device = next(model.parameters(), torch.empty(0)).device if hasattr(model, "parameters") else torch.device("cpu")
        x = x.to(device)
        with torch.inference_mode():
            y = model(x)
        if isinstance(y, (tuple, list)):
            y = y[0]
        if isinstance(y, dict):
            return {"feature": name, "output": {k: self._summarize(v) for k, v in y.items()}}
        return {"feature": name, "output": self._summarize(y)}

    @staticmethod
    def _summarize(value):
        if torch is not None and torch.is_tensor(value):
            t = value.detach().float().cpu()
            result = {
                "shape": list(t.shape),
                "min": float(t.min()) if t.numel() else None,
                "max": float(t.max()) if t.numel() else None,
                "mean": float(t.mean()) if t.numel() else None,
            }
            if t.numel() <= 32:
                result["values"] = t.flatten().tolist()
            if t.ndim == 2 and t.shape[0] == 1 and t.shape[1] > 1:
                result["predicted_index"] = int(t.argmax(dim=1).item())
            return result
        return str(value)

    def _file_to_tensor(self, name: str, content: bytes, filename: str):
        if torch is None:
            raise RuntimeError("PyTorch is not installed")
        suffix = Path(filename).suffix.lower()

        if suffix == ".npy":
            arr = np.load(io.BytesIO(content), allow_pickle=False)
        elif suffix == ".npz":
            z = np.load(io.BytesIO(content), allow_pickle=False)
            key = "image" if "image" in z.files else z.files[0]
            arr = z[key]
        elif suffix in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            from PIL import Image
            img = Image.open(io.BytesIO(content)).convert("RGB").resize((224, 224))
            arr = np.asarray(img, dtype=np.float32) / 255.0
            arr = np.transpose(arr, (2, 0, 1))
        elif suffix == ".dcm":
            import pydicom
            ds = pydicom.dcmread(io.BytesIO(content))
            arr = ds.pixel_array.astype(np.float32)
            arr -= arr.min()
            denom = max(float(arr.max()), 1.0)
            arr /= denom
        elif suffix == ".wav":
            with wave.open(io.BytesIO(content), "rb") as w:
                frames = w.readframes(w.getnframes())
                sample_width = w.getsampwidth()
                channels = w.getnchannels()
            dtype = np.int16 if sample_width == 2 else np.uint8
            arr = np.frombuffer(frames, dtype=dtype).astype(np.float32)
            if channels > 1:
                arr = arr.reshape(-1, channels).mean(axis=1)
            scale = max(float(np.abs(arr).max()), 1.0)
            arr /= scale
        else:
            raise ValueError(f"Unsupported input type: {suffix or 'unknown'}")

        arr = np.asarray(arr, dtype=np.float32)
        x = torch.from_numpy(arr)

        # Generic batch/channel normalization. Adjust this adapter to your exact model input.
        if name in {"mri", "ct"}:
            if x.ndim == 2:
                x = x.unsqueeze(0).unsqueeze(0)
            elif x.ndim == 3:
                x = x.unsqueeze(0)
        elif name == "cctv":
            if x.ndim == 3:
                x = x.unsqueeze(0)
        elif name == "audio":
            if x.ndim == 1:
                x = x.unsqueeze(0).unsqueeze(0)
            elif x.ndim == 2:
                x = x.unsqueeze(0)
        return x


registry = ModelRegistry()
