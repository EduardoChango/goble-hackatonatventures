import json
import urllib.error
import urllib.request
from typing import Any

from goble.domain.exceptions import ExternalServiceError


class HttpExternalDataProvider:
    """Adapter real hacia la API externa. Usa urllib para no requerir dependencias."""

    def __init__(self, base_url: str, api_key: str = "", timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        # TODO: ajustar ruta/método/headers al contrato real de la API
        request = urllib.request.Request(
            f"{self._base_url}/data/{query['reference']}",
            headers={"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ExternalServiceError(f"provider_api no disponible: {exc}") from exc
