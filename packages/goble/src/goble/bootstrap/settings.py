import os
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    use_mocks: bool
    mocks_dir: str
    jobs_table_name: str
    provider_api_url: str
    provider_api_key: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", "local"),
            use_mocks=_bool(os.getenv("USE_MOCKS", "true")),
            mocks_dir=os.getenv("MOCKS_DIR", str(_REPO_ROOT / "mocks" / "external_apis")),
            jobs_table_name=os.getenv("JOBS_TABLE_NAME", ""),
            provider_api_url=os.getenv("PROVIDER_API_URL", ""),
            provider_api_key=os.getenv("PROVIDER_API_KEY", ""),
        )
