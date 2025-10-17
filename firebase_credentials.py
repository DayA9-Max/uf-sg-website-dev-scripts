"""Utilities for loading Firebase service-account credentials.

This module centralizes the logic for reading the service-account JSON
configuration from environment variables or a `.env` file. The scripts in this
repository can import :func:`load_service_account_credentials` to keep their
set-up consistent and avoid duplicating error-handling code.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from firebase_admin import credentials


ENV_VAR_NAME = "FIREBASE_SERVICE_ACCOUNT"


def load_service_account_credentials(env_var: str = ENV_VAR_NAME):
    """Return a :class:`firebase_admin.credentials.Certificate` instance.

    The service-account configuration is loaded from ``env_var`` which can
    contain either the absolute path to a JSON file on disk or the JSON
    document itself. The environment variable may be provided directly via the
    shell or loaded from a `.env` file.

    Raises:
        RuntimeError: If the environment variable is missing, the referenced
            file is not found, or the provided JSON is invalid.
    """

    load_dotenv()

    raw_value = os.getenv(env_var)
    if not raw_value or not raw_value.strip():
        raise RuntimeError(
            f"{env_var} is not set. Provide the path to your service-account "
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
            f"{env_var} must be a path to a service-account JSON file or the "
            "JSON contents themselves."
        ) from exc

    if not isinstance(service_account_info, dict):
        raise RuntimeError(
            f"{env_var} JSON must decode to an object containing the "
            "service-account credentials."
        )

    return credentials.Certificate(service_account_info)


__all__ = ["load_service_account_credentials", "ENV_VAR_NAME"]

