"""Shared data models for UF SG legislation processing scripts."""

import re
from typing import Any

from pydantic import BaseModel, Field, validator


_BILL_ID_PATTERN = re.compile(r"^(?:SSB\s+)?\d{4}-\d{4}$")
_ALLOWED_STATUSES = {"PASSED", "TBD"}


class BillMetadata(BaseModel):
    """Metadata describing a single piece of Student Government legislation."""

    id: str = Field(..., description="Bill identifier, e.g. 'SSB 2024-0001'.")
    title: str = Field(default="", description="Official title of the legislation.")
    author: str = Field(default="", description="Primary author of the legislation.")
    sponsor: str = Field(default="", description="Sponsor(s) for the legislation.")
    summary: str = Field(default="", description="Summary of the legislation (100 word max).")
    status: str = Field(default="TBD", description="Current status of the legislation.")

    @validator("id")
    def _validate_id(cls, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("id may not be empty")
        if not _BILL_ID_PATTERN.match(text):
            raise ValueError("id must match 'SSB ####-####' or '####-####'")
        return text

    @validator("title", "author", "sponsor", pre=True, always=True)
    def _default_optional_strings(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @validator("summary", pre=True, always=True)
    def _validate_summary(cls, value: Any) -> str:
        text = "" if value is None else " ".join(str(value).split())
        words = text.split()
        if len(words) > 100:
            text = " ".join(words[:100])
        return text

    @validator("status", pre=True, always=True)
    def _validate_status(cls, value: Any) -> str:
        if not value:
            return "TBD"
        normalized = str(value).strip().upper()
        if normalized not in _ALLOWED_STATUSES:
            raise ValueError("status must be one of PASSED or TBD")
        return normalized

    class Config:
        anystr_strip_whitespace = True
        validate_assignment = True
        allow_mutation = False
        use_enum_values = True
