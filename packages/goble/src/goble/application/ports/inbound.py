"""Puertos de entrada (driving): lo que el hexágono ofrece al exterior.

Los adapters de entrada (lambdas, Flask) dependen de estos contratos.
"""

from typing import Any, Protocol

from goble.domain.models import Job


class ProcessJobPort(Protocol):
    def execute(self, payload: dict[str, Any]) -> Job: ...


class GetJobPort(Protocol):
    def execute(self, job_id: str) -> Job: ...
