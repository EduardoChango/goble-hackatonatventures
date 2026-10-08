from typing import Any

from goble.application.ports.outbound import ExternalDataProvider, JobRepository
from goble.domain.exceptions import ExternalServiceError, InvalidPayloadError
from goble.domain.models import Job

REQUIRED_FIELDS = ("reference",)


class ProcessJob:
    def __init__(self, repository: JobRepository, provider: ExternalDataProvider) -> None:
        self._repository = repository
        self._provider = provider

    def execute(self, payload: dict[str, Any]) -> Job:
        missing = [f for f in REQUIRED_FIELDS if not payload.get(f)]
        if missing:
            raise InvalidPayloadError(f"Campos requeridos faltantes: {', '.join(missing)}")

        job = Job(payload=payload)
        try:
            job.complete(self._provider.fetch(payload))
        except ExternalServiceError as exc:
            job.fail(str(exc))

        self._repository.save(job)
        return job
