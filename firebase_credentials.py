"""Utilities for loading Firebase service-account credentials.

This module centralizes the logic for reading the service-account JSON
configuration from environment variables or a `.env` file. The scripts in this
repository can import :func:`load_service_account_credentials` to keep their
set-up consistent and avoid duplicating error-handling code.
"""

from __future__ import annotations

import json
from pathlib import Path

from firebase_admin import credentials

from config import FIREBASE_SERVICE_ACCOUNT, FIREBASE_SERVICE_ACCOUNT_ENV_VAR


ENV_VAR_NAME = FIREBASE_SERVICE_ACCOUNT_ENV_VAR


def load_service_account_credentials(raw_value: str | None = None):
    f"""Return a :class:`firebase_admin.credentials.Certificate` instance.

    The service-account configuration is loaded from ``raw_value`` which can
    contain either the absolute path to a JSON file on disk or the JSON
    document itself. When omitted, the value falls back to the
    :mod:`config`-managed environment variable
    :data:`FIREBASE_SERVICE_ACCOUNT_ENV_VAR` (``{ENV_VAR_NAME}``).

    Raises:
        RuntimeError: If the environment variable is missing, the referenced
            file is not found, or the provided JSON is invalid.
    """

    raw_value = (raw_value or FIREBASE_SERVICE_ACCOUNT or "").strip()
    if not raw_value:
        raise RuntimeError(
            f"{ENV_VAR_NAME} is not set. Provide the path to your service-account "
            "JSON file or the JSON contents in this environment variable "
            "(e.g., via a .env file)."
        )

    candidate_path = Path(raw_value).expanduser()
    if candidate_path.is_file():
        return credentials.Certificate(str(candidate_path))

    try:
        service_account_info = json.loads(raw_value)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive branch
        raise RuntimeError(
            f"{ENV_VAR_NAME} must be a path to a service-account JSON file or the "
            "JSON contents themselves."
        ) from exc

    if not isinstance(service_account_info, dict):
        raise RuntimeError(
            f"{ENV_VAR_NAME} JSON must decode to an object containing the "
            "service-account credentials."
        )

    return credentials.Certificate(service_account_info)


__all__ = ["load_service_account_credentials", "ENV_VAR_NAME"]

