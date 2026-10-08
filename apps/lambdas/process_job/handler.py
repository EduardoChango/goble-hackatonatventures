"""Adapter de entrada: API Gateway POST /jobs -> caso de uso ProcessJob."""

import json
import logging

from goble.adapters.inbound.http import parse_body, response
from goble.bootstrap import container
from goble.domain.exceptions import InvalidPayloadError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    try:
        payload = parse_body(event)
        job = container.process_job().execute(payload)
        return response(201, job.to_dict())
    except (InvalidPayloadError, json.JSONDecodeError) as exc:
        return response(400, {"error": str(exc)})
    except Exception:
        logger.exception("Error no controlado procesando job")
        return response(500, {"error": "Internal server error"})
