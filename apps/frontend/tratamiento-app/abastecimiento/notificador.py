"""Notificador: arma el email de cada evento y lo envía por SES al cuidador y al paciente.

Modos:
- SES (EMAIL_REMITENTE definido): envía con Amazon SES v2.
- Simulado (sin remitente): no envía; deja el email completo en evento_log para la consola de demo.
Si SES falla (sandbox, permisos), se registra NotificacionFallida y no se corta el flujo.

EMAIL_DESTINO_DEMO: si está definido, TODOS los emails van a esa casilla (SES en sandbox solo
entrega a correos verificados y los cuidadores de prueba son @demo.ec). El cuerpo indica a quién iban.
"""
import html
import logging
import os
import uuid

import db
from abastecimiento import eventos

log = logging.getLogger(__name__)

ESTADO_TEXTO = {"por_agotarse": "se acaba pronto", "agotado": "ya se acabó",
                "sin_respuesta": "el IESS aún no responde", "parcial": "el IESS entregó solo una parte",
                "no": "el IESS no la entregó"}


def destinatarios(detail):
    """Cuidadores del evento + el paciente (si tiene login con email)."""
    correos = [c["email"] for c in detail.get("cuidadores", []) if c.get("email")]
    if detail.get("paciente_id"):
        u = db._uno("SELECT email FROM usuario WHERE paciente_id = %s", detail["paciente_id"])
        if u:
            correos.append(u["email"])
    return list(dict.fromkeys(correos))  # sin repetidos, en orden


def _fecha(iso):
    d, m = int(iso[8:10]), int(iso[5:7])
    return f"{d}/{m}"


def armar(detail_type, detail):
    """(asunto, texto, html) del email. None si el evento no se notifica por email."""
    paciente = detail.get("paciente", "tu paciente")
    lineas, extra = [], []
    if detail_type == "MedicacionPorAgotarse":
        meds = detail["medicamentos"]
        primero = meds[0]
        cuando = ("ya se acabó" if primero["estado"] == "agotado"
                  else f"se acaba en {primero['dias_restantes']} días ({_fecha(primero['fecha_agotamiento'])})")
        asunto = f"{paciente}: {primero['nombre']} {cuando}"
        lineas.append(f"Revisamos la medicación de {paciente}:")
        for m in meds:
            estado = ("ya se acabó" if m["estado"] == "agotado"
                      else f"alcanza hasta el {_fecha(m['fecha_agotamiento'])} ({m['dias_restantes']} días)")
            nota = " · retiro presencial con receta especial" if m.get("solo_retiro") else ""
            lineas.append(f"• {m['nombre']} {m['concentracion']}: {estado}. "
                          f"Para un mes: {m['cantidad_sugerida']} unidades{nota}.")
        if detail.get("productos_sugeridos"):
            extra.append("También podría necesitar:")
            extra += [f"• {p['nombre']}: {p['motivo']}" for p in detail["productos_sugeridos"][:3]]
    elif detail_type == "EntregaIessIncompleta":
        asunto = f"{paciente}: el IESS no completó la entrega de medicinas"
        lineas.append(f"Estado de la entrega del IESS para {paciente}:")
        for m in detail["medicamentos"]:
            lineas.append(f"• {m['nombre']} {m['concentracion']}: {ESTADO_TEXTO.get(m['estado_iess'], m['estado_iess'])}"
                          f" (faltan {m['falta']} de {m['total']}).")
    elif detail_type == "PedidoActualizado":
        asunto = f"{paciente}: tu pedido está {detail.get('estado', 'actualizado')}"
        lineas.append(f"Pedido {detail.get('pedido_id', '')} en {detail.get('farmacia', 'la farmacia')}: "
                      f"{detail.get('estado', '')}.")
    else:
        return None

    farmacias = detail.get("farmacias_sugeridas") or []
    if farmacias:
        lineas.append("")
        lineas.append("Farmacias de Farmaenlace con stock:")
        for f in farmacias:
            completa = "tiene todo" if f.get("completa") else "tiene una parte"
            lineas.append(f"• {f['nombre']} ({f['direccion']}): {f['km']} km de {f['mas_cerca_de']}, {completa}.")
    pie = [""] + ([f"Abrir la app: {os.environ['APP_URL']}"] if os.getenv("APP_URL") else [])
    texto = "\n".join(lineas + ([""] + extra if extra else []) + pie
                      + ["Este aviso no reemplaza la indicación médica."])
    cuerpo = "".join(f"<p>{html.escape(x)}</p>" if x else "<br>" for x in texto.splitlines())
    return asunto, texto, f"<div style=\"font-family:Arial,sans-serif;font-size:15px\">{cuerpo}</div>"


def notificar(detail_type, detail):
    """Envía (o simula) el email del evento. Devuelve un resumen."""
    contenido = armar(detail_type, detail)
    if contenido is None:
        return {"enviado": False, "motivo": "evento sin email"}
    asunto, texto, cuerpo_html = contenido
    para = destinatarios(detail)
    demo = os.getenv("EMAIL_DESTINO_DEMO", "")
    if demo:
        nota = f"[Demo] Este aviso iba para: {', '.join(para) or 'nadie'}"
        texto, cuerpo_html, para = f"{nota}\n\n{texto}", f"<p><i>{html.escape(nota)}</i></p>{cuerpo_html}", [demo]
    remitente = os.getenv("EMAIL_REMITENTE", "")
    resumen = {"evento_id": detail.get("evento_id"), "paciente_id": detail.get("paciente_id"),
               "evento": detail_type, "para": para, "asunto": asunto, "texto": texto,
               "modo": "ses" if remitente else "simulado"}
    if not para:
        resumen["modo"] = "sin destinatarios"
    elif remitente:
        try:
            import boto3
            r = boto3.client("sesv2").send_email(
                FromEmailAddress=remitente, Destination={"ToAddresses": para},
                Content={"Simple": {"Subject": {"Data": asunto, "Charset": "UTF-8"},
                                    "Body": {"Text": {"Data": texto, "Charset": "UTF-8"},
                                             "Html": {"Data": cuerpo_html, "Charset": "UTF-8"}}}})
            resumen["message_id"] = r.get("MessageId")
        except Exception as e:  # noqa: BLE001 - sandbox de SES, permisos: se registra y se sigue
            log.exception("SES no pudo enviar %s", detail_type)
            resumen["error"] = str(e)
            eventos.registrar(str(uuid.uuid4()), "interno", "NotificacionFallida", resumen)
            return {**resumen, "enviado": False}
    eventos.registrar(str(uuid.uuid4()), "interno", "NotificacionEnviada", resumen)
    return {**resumen, "enviado": resumen["modo"] == "ses"}
