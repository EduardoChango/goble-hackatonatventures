"""Empaqueta el core `goble` y los mocks como Lambda Layer en build/layer/.

Estructura resultante (montada en /opt dentro de Lambda):
    build/layer/python/goble/...           -> importable como `goble`
    build/layer/mocks/external_apis/...    -> MOCKS_DIR=/opt/mocks/external_apis
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / "build" / "layer"


def main() -> None:
    shutil.rmtree(LAYER, ignore_errors=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(ROOT / "packages" / "goble" / "src" / "goble", LAYER / "python" / "goble", ignore=ignore)
    shutil.copytree(ROOT / "mocks" / "external_apis", LAYER / "mocks" / "external_apis")
    print(f"Layer generado en {LAYER}")


if __name__ == "__main__":
    main()
