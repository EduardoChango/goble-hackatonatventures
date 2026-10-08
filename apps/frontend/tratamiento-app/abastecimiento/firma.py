"""Firma HMAC-SHA256 de los callbacks entre Farmaenlace y el módulo.

Farmaenlace firma el cuerpo con el secreto compartido y lo envía en el header X-Farmaenlace-Firma;
el módulo rechaza cualquier callback cuya firma no coincida.
"""
import hashlib
import hmac
import os

HEADER = "X-Farmaenlace-Firma"


def secreto():
    return os.getenv("FARMAENLACE_WEBHOOK_SECRET", "solo-para-desarrollo-local")


def firmar(cuerpo: bytes) -> str:
    return hmac.new(secreto().encode(), cuerpo, hashlib.sha256).hexdigest()


def verificar(cuerpo: bytes, firma: str | None) -> bool:
    return bool(firma) and hmac.compare_digest(firmar(cuerpo), firma)
