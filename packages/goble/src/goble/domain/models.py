"""Entidades del dominio. Sin dependencias de frameworks ni de AWS.

`Job` es un placeholder: renómbralo a la entidad real del negocio.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class JobStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Job:
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def complete(self, result: dict[str, Any]) -> None:
        self.status = JobStatus.COMPLETED
        self.result = result
        self.error = None
        self.updated_at = _now()

    def fail(self, error: str) -> None:
        self.status = JobStatus.FAILED
        self.error = error
        self.updated_at = _now()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        return cls(**{**data, "status": JobStatus(data["status"])})
