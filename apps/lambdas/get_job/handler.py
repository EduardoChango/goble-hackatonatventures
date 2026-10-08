"""Adapter de entrada: API Gateway GET /jobs/{job_id} -> caso de uso GetJob."""

import logging

from goble.adapters.inbound.http import response
from goble.bootstrap import container
from goble.domain.exceptions import JobNotFoundError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    job_id = (event.get("pathParameters") or {}).get("job_id")
    if not job_id:
        return response(400, {"error": "job_id es requerido"})
    try:
        return response(200, container.get_job().execute(job_id).to_dict())
    except JobNotFoundError as exc:
        return response(404, {"error": str(exc)})
    except Exception:
        logger.exception("Error no controlado obteniendo job")
        return response(500, {"error": "Internal server error"})
