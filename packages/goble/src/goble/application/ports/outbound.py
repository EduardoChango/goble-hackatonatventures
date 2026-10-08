"""Puertos de salida (driven): lo que el hexágono necesita del exterior.

Cada puerto tiene al menos un adapter real y uno mock/in-memory.
"""

from typing import Any, Protocol

from goble.domain.models import Job


class JobRepository(Protocol):
    def save(self, job: Job) -> None: ...

    def get(self, job_id: str) -> Job | None: ...


class ExternalDataProvider(Protocol):
    """API externa a la que el proyecto se conecta (placeholder: `provider_api`)."""

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]: ...
