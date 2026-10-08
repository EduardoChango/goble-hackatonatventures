"""Empaqueta el layer y las lambdas como zips listos para subir a S3.

Salida en build/artifacts/:
    layer-<hash>.zip         -> python/goble/... + mocks/external_apis/... (montado en /opt)
    process_job-<hash>.zip   -> handler.py
    get_job-<hash>.zip       -> handler.py
    keys.env                 -> nombres de los zips (lo lee infra/deploy.sh)

El hash depende del contenido: si el código no cambia, el nombre tampoco, y CloudFormation
no actualiza la lambda. Si cambia, el nombre nuevo fuerza la actualización.
"""

import hashlib
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "artifacts"
LAMBDAS = ["process_job", "get_job"]


def _files(src: Path) -> list[Path]:
    return sorted(
        p for p in src.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )


def build_zip(name: str, sources: list[tuple[Path, str]]) -> str:
    """sources: (carpeta local, prefijo dentro del zip)."""
    entries = [(f, f"{prefix}{f.relative_to(src).as_posix()}") for src, prefix in sources for f in _files(src)]

    digest = hashlib.sha256()
    for path, arcname in entries:
        digest.update(arcname.encode())
        digest.update(path.read_bytes())
    filename = f"{name}-{digest.hexdigest()[:10]}.zip"

    with zipfile.ZipFile(OUT / filename, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in entries:
            zf.write(path, arcname)
    return filename


def main() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)

    keys = {
        "LAYER_ZIP": build_zip(
            "layer",
            [
                (ROOT / "packages" / "goble" / "src" / "goble", "python/goble/"),
                (ROOT / "mocks" / "external_apis", "mocks/external_apis/"),
            ],
        )
    }
    for name in LAMBDAS:
        keys[f"{name.upper()}_ZIP"] = build_zip(name, [(ROOT / "apps" / "lambdas" / name, "")])

    (OUT / "keys.env").write_text("".join(f"{k}={v}\n" for k, v in keys.items()), encoding="utf-8")
    for v in keys.values():
        print(f"  build/artifacts/{v}")


if __name__ == "__main__":
    main()
