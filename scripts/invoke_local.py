"""Invoca un handler de Lambda en local con un evento mock.

Uso:
    python scripts/invoke_local.py process_job mocks/entrypoint/events/process_job.json
"""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "goble" / "src"))


def main(lambda_name: str, event_path: str) -> None:
    handler_file = ROOT / "apps" / "lambdas" / lambda_name / "handler.py"
    spec = importlib.util.spec_from_file_location(f"{lambda_name}_handler", handler_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    result = module.handler(event, None)
    result["body"] = json.loads(result["body"])
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
