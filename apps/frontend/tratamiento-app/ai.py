"""Lectura de la receta a partir de una foto.

EDU: este es el archivo para conectar IA de verdad. Tres modos:
- AI_PROVIDER=bedrock (así se despliega en AWS): Claude en Amazon Bedrock con las credenciales
  de la Lambda (rol IAM, sin API key). Requiere `pip install "anthropic[bedrock]"` y acceso al
  modelo habilitado en la consola de Bedrock.
- ANTHROPIC_API_KEY definida: API de Anthropic directa (útil en local).
- Ninguno: devuelve una receta de EJEMPLO (la pantalla lo avisa con un cartel).
Si algo falla (sin acceso al modelo, foto ilegible, formato no soportado), cae al ejemplo.
Formato de salida: {"origen": "ia" | "simulado", "medicamentos": [ {nombre, dosis_mg, cada_horas, dias}, ... ]}
"""
import base64
import json
import os

EJEMPLO = [
    {"nombre": "Losartán", "dosis_mg": 100, "cada_horas": 24, "dias": 30},
    {"nombre": "Metformina", "dosis_mg": 1000, "cada_horas": 12, "dias": 30},
    {"nombre": "Atorvastatina", "dosis_mg": 20, "cada_horas": 24, "dias": 30},
    {"nombre": "Amlodipino", "dosis_mg": 5, "cada_horas": 24, "dias": 30},
]

PROMPT = (
    "Lee esta receta médica. Responde SOLO con JSON, sin texto extra, con esta forma: "
    '{"medicamentos":[{"nombre":"...","dosis_mg":0,"cada_horas":0,"dias":0}]}. '
    "Usa el nombre genérico. Si un dato no se ve, usa null. No inventes datos."
)
FORMATOS = {"image/jpeg", "image/png", "image/gif", "image/webp"}
# Modelos que aceptan `fallbacks: "default"` en la API directa de Anthropic
FALLBACK_SERVIDOR = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


def _cliente():
    """(cliente, modelo) según el entorno, o (None, None) si no hay IA configurada."""
    import anthropic

    if os.getenv("AI_PROVIDER") == "bedrock":
        region = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION") or "us-east-1"
        # Bedrock no tiene el parámetro `fallbacks` del servidor: si el modelo rechaza la petición,
        # el middleware del SDK reintenta con el modelo de respaldo.
        respaldo = os.getenv("CLAUDE_FALLBACK_MODEL", "anthropic.claude-opus-4-8")
        cliente = anthropic.AnthropicBedrockMantle(
            aws_region=region, middleware=[anthropic.BetaRefusalFallbackMiddleware([{"model": respaldo}])])
        return cliente, os.getenv("CLAUDE_MODEL", "anthropic.claude-sonnet-5")
    if os.getenv("ANTHROPIC_API_KEY"):
        return anthropic.Anthropic(), os.getenv("CLAUDE_MODEL", "claude-sonnet-5")
    return None, None


def _leer_con_ia(imagen, mime):
    cliente, modelo = _cliente()
    if cliente is None:
        return None
    extra = {}
    if os.getenv("AI_PROVIDER") != "bedrock" and modelo in FALLBACK_SERVIDOR:
        # API directa: si el modelo rechaza, el servidor reintenta solo con otro modelo
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    msg = cliente.beta.messages.create(
        model=modelo,
        max_tokens=2000,
        output_config={"effort": "low"},  # extracción simple: menos razonamiento, respuesta más rápida
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": mime,
                                         "data": base64.b64encode(imagen).decode()}},
            {"type": "text", "text": PROMPT},
        ]}],
        **extra,
    )
    if msg.stop_reason == "refusal":
        print("[ai.py] El modelo rechazó leer la receta")
        return None
    texto = next(b.text for b in msg.content if b.type == "text")
    datos = json.loads(texto[texto.index("{"): texto.rindex("}") + 1])
    meds = [m for m in datos.get("medicamentos", []) if m.get("nombre")]
    if not meds:
        return None
    return {"origen": "ia", "medicamentos": [
        {"nombre": m["nombre"], "dosis_mg": m.get("dosis_mg") or 0,
         "cada_horas": m.get("cada_horas") or 24, "dias": m.get("dias") or 30}
        for m in meds]}


def extraer_receta(imagen, mime="image/jpeg"):
    if imagen and mime in FORMATOS:
        try:
            resultado = _leer_con_ia(imagen, mime)
            if resultado:
                return resultado
        except Exception as e:  # noqa: BLE001 - en demo preferimos caer al ejemplo
            print("[ai.py] No se pudo leer la receta con IA:", e)
    return {"origen": "simulado", "medicamentos": EJEMPLO}
