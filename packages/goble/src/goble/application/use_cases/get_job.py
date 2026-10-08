from goble.application.ports.outbound import JobRepository
from goble.domain.exceptions import JobNotFoundError
from goble.domain.models import Job


class GetJob:
    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def execute(self, job_id: str) -> Job:
        job = self._repository.get(job_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} no encontrado")
        return job
