from __future__ import annotations

import json
import base64
from pathlib import Path
import os
from utils.config import LEMMA_DIR_NAME

USERS_DIR_NAME = "users"
CURRENT_USER_FILENAME = "current_user"

def get_lemma_dir() -> Path:
    """
    Get Lemma toolkit directory path

    Returns:
        Path to ~/.lemma directory
    """
    env_lemma_dir = os.getenv("LEMMA_HOME")
    if env_lemma_dir:
        lemma_dir = Path(env_lemma_dir)
    else:
        lemma_dir = Path.home() / LEMMA_DIR_NAME
    lemma_dir.mkdir(parents=True, exist_ok=True)
    return lemma_dir.resolve()


def _sanitize_user_identifier(user_identifier: str) -> str:
    """Return a safe folder name for a user identifier (e.g. email).

    Currently emails are safe for filesystem usage on macOS/Linux. As a
    precaution, we trim spaces and avoid path separators.
    """
    if not user_identifier:
        return user_identifier
    # Basic hardening to avoid any accidental path traversal
    sanitized = user_identifier.strip().replace("/", "_")
    return sanitized


def get_current_user() -> str | None:
    """Read the current user (email) from ~/.lemma/current_user.

    Returns None if not set or file missing/empty.
    """
    current_path = get_lemma_dir() / CURRENT_USER_FILENAME
    # print(f"Current user path: {current_path}")
    try:
        if not current_path.exists():
            return None
        content = current_path.read_text(encoding="utf-8").strip()
        return content or None
    except Exception:
        return None


def set_current_user(user_email: str) -> None:
    """Write current user (email) to ~/.lemma/current_user."""
    current_path = get_lemma_dir() / CURRENT_USER_FILENAME
    current_path.write_text(user_email.strip(), encoding="utf-8")


def clear_current_user() -> None:
    """Remove ~/.lemma/current_user if it exists."""
    current_path = get_lemma_dir() / CURRENT_USER_FILENAME
    try:
        if current_path.exists():
            current_path.unlink()
    except Exception:
        # Best-effort; ignore failures here
        pass


def get_user_working_dir(user_email: str | None) -> Path:
    """Return the working directory for a given user under ~/.lemma/users/EMAIL.

    """
    if not user_email:
        raise ValueError("Can not get user working directory for current user")
    sanitized = _sanitize_user_identifier(user_email)
    path = get_lemma_dir() / USERS_DIR_NAME / sanitized
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()

def extract_user_from_lemma_credential(access_token: str) -> str | None:
    """Extract user email from Lemma dynamic_credential.json by decoding JWT.

    The dynamic credential schema (support/py/proto/credential_models.py)
    contains an `accessToken` (JWT). We decode its payload and read the
    `mail` field as the user's email. Fallback to `email` if present.
    """
    try:
        if not access_token or access_token.count(".") < 2:
            return None
        # JWT: header.payload.signature -> we want payload
        payload_b64 = access_token.split(".")[1]
        # Add '=' padding to make it base64-decodable
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload_json = base64.b64decode(padded).decode("utf-8")
        payload = json.loads(payload_json)

        # Commonly 'mail' is used
        return _sanitize_user_identifier(payload.get("mail"))
    except Exception:
        return None