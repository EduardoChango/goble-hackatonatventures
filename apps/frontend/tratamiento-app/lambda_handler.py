"""Entrada de AWS Lambda: API Gateway (HTTP API) -> Flask, sin cambiar la app."""
from apig_wsgi import make_lambda_handler

from app import app

# binary_support: los íconos PNG y las fotos de recetas viajan en base64
handler = make_lambda_handler(app, binary_support=True)
