import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional

TOKEN_SECRET = os.getenv("RAM_TOKEN_SECRET", "CHANGE_THIS_IN_PRODUCTION")
TOKEN_TTL_SECONDS = int(os.getenv("RAM_TOKEN_TTL_SECONDS", "604800"))


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${_b64(salt)}${_b64(key)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, salt_b64, key_b64 = encoded.split("$", 2)
        if scheme != "scrypt":
            return False
        salt = _unb64(salt_b64)
        expected = _unb64(key_b64)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def create_token(subject: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "RAM"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": subject, "exp": int(time.time()) + TOKEN_TTL_SECONDS}, separators=(",", ":")).encode())
    message = f"{header}.{payload}".encode()
    sig = _b64(hmac.new(TOKEN_SECRET.encode(), message, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def verify_token(token: str) -> Optional[str]:
    try:
        header, payload, sig = token.split(".", 2)
        message = f"{header}.{payload}".encode()
        expected = _b64(hmac.new(TOKEN_SECRET.encode(), message, hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_unb64(payload))
        if int(data["exp"]) < int(time.time()):
            return None
        return str(data["sub"])
    except Exception:
        return None
