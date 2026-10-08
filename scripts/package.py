"""Empaqueta tratamiento-app como zip listo para subir a S3 (lo usan las Lambdas de la app y db-init).

Salida en build/artifacts/:
    frontend-<hash>.zip   -> tratamiento-app + dependencias (Linux) + db/init como db_init/
                             + db/datos_farmaenlace como db_datos/
    keys.env              -> nombre del zip (lo leen infra/deploy.ps1 y infra/deploy.sh)

El hash depende del contenido: si el código no cambia, el nombre tampoco, y CloudFormation
no actualiza la lambda. Si cambia, el nombre nuevo fuerza la actualización.
"""

import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "artifacts"
APP = ROOT / "apps" / "frontend" / "tratamiento-app"
# Carpetas de la app que no van a la Lambda
APP_EXCLUIR = {"tests", "data", ".venv", "__pycache__"}


def _files(src: Path, excluir: set[str] = frozenset()) -> list[Path]:
    return sorted(
        p for p in src.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        and not excluir.intersection(p.relative_to(src).parts)
    )


def build_zip(name: str, sources: list[tuple]) -> str:
    """sources: (carpeta local, prefijo dentro del zip[, carpetas a excluir de esa fuente])."""
    entries = [(f, f"{src[1]}{f.relative_to(src[0]).as_posix()}")
               for src in sources for f in _files(src[0], src[2] if len(src) > 2 else frozenset())]

    digest = hashlib.sha256()
    for path, arcname in entries:
        digest.update(arcname.encode())
        digest.update(path.read_bytes())
    filename = f"{name}-{digest.hexdigest()[:10]}.zip"

    with zipfile.ZipFile(OUT / filename, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in entries:
            zf.write(path, arcname)
    return filename


def frontend_deps() -> Path:
    """Instala requirements.txt de la app con wheels para Lambda (Linux x86_64, Python 3.12).

    Se cachea por hash de requirements.txt: solo reinstala si cambian las dependencias.
    """
    req = APP / "requirements.txt"
    destino = ROOT / "build" / f"deps-{hashlib.sha256(req.read_bytes()).hexdigest()[:10]}"
    if not destino.exists():
        tmp = destino.with_suffix(".tmp")
        shutil.rmtree(tmp, ignore_errors=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "-r", str(req), "--target", str(tmp),
                        "--platform", "manylinux2014_x86_64", "--implementation", "cp",
                        "--python-version", "3.12", "--only-binary=:all:"], check=True)
        tmp.rename(destino)
    return destino


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)  # en OneDrive, borrar y recrear la carpeta puede fallar
    for viejo in OUT.iterdir():
        viejo.unlink()

    keys = {"FRONTEND_ZIP": build_zip("frontend", [
        (frontend_deps(), ""),
        (APP, "", APP_EXCLUIR),
        (ROOT / "db" / "init", "db_init/"),
        (ROOT / "db" / "datos_farmaenlace", "db_datos/"),
    ])}

    (OUT / "keys.env").write_text("".join(f"{k}={v}\n" for k, v in keys.items()), encoding="utf-8")
    for v in keys.values():
        print(f"  build/artifacts/{v}")


if __name__ == "__main__":
    main()
