"""Composition root: único lugar que decide qué adapter implementa cada puerto."""

from functools import lru_cache

from goble.adapters.outbound.external_api.http_provider import HttpExternalDataProvider
from goble.adapters.outbound.external_api.mock_provider import MockExternalDataProvider
from goble.adapters.outbound.persistence.dynamodb_repository import DynamoDBJobRepository
from goble.adapters.outbound.persistence.in_memory_repository import InMemoryJobRepository
from goble.application.ports.outbound import ExternalDataProvider, JobRepository
from goble.application.use_cases.get_job import GetJob
from goble.application.use_cases.process_job import ProcessJob
from goble.bootstrap.settings import Settings


@lru_cache
def settings() -> Settings:
    return Settings.from_env()


@lru_cache
def job_repository() -> JobRepository:
    s = settings()
    if s.jobs_table_name:
        return DynamoDBJobRepository(s.jobs_table_name)
    return InMemoryJobRepository()


@lru_cache
def external_data_provider() -> ExternalDataProvider:
    s = settings()
    if s.use_mocks:
        return MockExternalDataProvider(s.mocks_dir)
    return HttpExternalDataProvider(s.provider_api_url, s.provider_api_key)


def process_job() -> ProcessJob:
    return ProcessJob(job_repository(), external_data_provider())


def get_job() -> GetJob:
    return GetJob(job_repository())
