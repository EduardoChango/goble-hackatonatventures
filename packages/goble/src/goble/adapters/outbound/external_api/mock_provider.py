import json
from pathlib import Path
from typing import Any

from goble.domain.exceptions import ExternalServiceError


class MockExternalDataProvider:
    """Simula la API externa leyendo fixtures de mocks/external_apis/provider_api/.

    Escenario = `<reference>.json`; si no existe se usa `default.json`.
    Fixtures con `status_code >= 400` simulan errores de la API.
    """

    def __init__(self, mocks_dir: str | Path, api_name: str = "provider_api") -> None:
        self._dir = Path(mocks_dir) / api_name

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        fixture = self._dir / f"{query.get('reference')}.json"
        if not fixture.exists():
            fixture = self._dir / "default.json"

        data = json.loads(fixture.read_text(encoding="utf-8"))
        if data.get("status_code", 200) >= 400:
            raise ExternalServiceError(
                f"provider_api respondió {data['status_code']}: {data.get('body')}"
            )
        return data["body"]
