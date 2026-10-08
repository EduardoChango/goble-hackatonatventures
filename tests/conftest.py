import json
from pathlib import Path

import pytest

from goble.adapters.outbound.external_api.mock_provider import MockExternalDataProvider
from goble.adapters.outbound.persistence.in_memory_repository import InMemoryJobRepository

ROOT = Path(__file__).resolve().parents[1]
MOCKS = ROOT / "mocks"


@pytest.fixture
def repository() -> InMemoryJobRepository:
    return InMemoryJobRepository()


@pytest.fixture
def provider() -> MockExternalDataProvider:
    return MockExternalDataProvider(MOCKS / "external_apis")


@pytest.fixture
def load_payload():
    def _load(name: str) -> dict:
        return json.loads((MOCKS / "entrypoint" / "payloads" / f"{name}.json").read_text("utf-8"))

    return _load
