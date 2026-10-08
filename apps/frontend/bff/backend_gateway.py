"""Puerto + adapters que usa el BFF para hablar con el backend.

- LocalBackend: invoca los casos de uso de `goble` en proceso (sin AWS, ideal para demo/mock).
- HttpBackend: llama a API Gateway desplegado.
"""

import os
from typing import Any, Protocol

import requests

from goble.bootstrap import container
from goble.domain.exceptions import InvalidPayloadError, JobNotFoundError


class BackendError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class BackendGateway(Protocol):
    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def get_job(self, job_id: str) -> dict[str, Any]: ...


class LocalBackend:
    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return container.process_job().execute(payload).to_dict()
        except InvalidPayloadError as exc:
            raise BackendError(400, str(exc)) from exc

    def get_job(self, job_id: str) -> dict[str, Any]:
        try:
            return container.get_job().execute(job_id).to_dict()
        except JobNotFoundError as exc:
            raise BackendError(404, str(exc)) from exc


class HttpBackend:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def _call(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        resp = requests.request(method, f"{self._base_url}{path}", timeout=15, **kwargs)
        if resp.status_code >= 400:
            raise BackendError(resp.status_code, resp.json().get("error", resp.text))
        return resp.json()

    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", "/jobs", json=payload)

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self._call("GET", f"/jobs/{job_id}")


def build_backend() -> BackendGateway:
    if os.getenv("BACKEND_MODE", "local") == "http":
        return HttpBackend(os.environ["API_BASE_URL"])
    return LocalBackend()
