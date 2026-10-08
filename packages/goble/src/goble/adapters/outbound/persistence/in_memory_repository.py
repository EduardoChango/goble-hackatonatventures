from goble.domain.models import Job


class InMemoryJobRepository:
    """Para tests y desarrollo local. No persiste entre invocaciones de Lambda."""

    def __init__(self) -> None:
        self._items: dict[str, dict] = {}

    def save(self, job: Job) -> None:
        self._items[job.id] = job.to_dict()

    def get(self, job_id: str) -> Job | None:
        data = self._items.get(job_id)
        return Job.from_dict(data) if data else None
