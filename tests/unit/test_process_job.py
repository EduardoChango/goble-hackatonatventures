import pytest

from goble.application.use_cases.get_job import GetJob
from goble.application.use_cases.process_job import ProcessJob
from goble.domain.exceptions import InvalidPayloadError, JobNotFoundError
from goble.domain.models import JobStatus


def test_process_job_completes_with_provider_data(repository, provider, load_payload):
    job = ProcessJob(repository, provider).execute(load_payload("sample_job"))

    assert job.status is JobStatus.COMPLETED
    assert job.result["status"] == "APPROVED"
    assert GetJob(repository).execute(job.id).id == job.id


def test_process_job_fails_when_provider_errors(repository, provider, load_payload):
    job = ProcessJob(repository, provider).execute(load_payload("sample_job_api_error"))

    assert job.status is JobStatus.FAILED
    assert "503" in job.error


def test_process_job_rejects_invalid_payload(repository, provider, load_payload):
    with pytest.raises(InvalidPayloadError):
        ProcessJob(repository, provider).execute(load_payload("sample_job_invalid"))


def test_get_job_not_found(repository):
    with pytest.raises(JobNotFoundError):
        GetJob(repository).execute("missing")
