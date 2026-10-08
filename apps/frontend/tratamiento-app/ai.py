"""Lectura de la receta a partir de una foto.

EDU: este es el archivo para conectar IA de verdad.
- Sin clave de API, devuelve una receta de EJEMPLO (la pantalla lo avisa con un cartel).
- Con la variable de entorno ANTHROPIC_API_KEY (y `pip install anthropic`), intenta leer la foto.
  Esa parte NO está probada: revísenla antes de la demo. Si algo falla, cae al ejemplo.
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


def extraer_receta(imagen, mime="image/jpeg"):
    key = os.getenv("ANTHROPIC_API_KEY")
    if key and imagen:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            msg = client.messages.create(
                model=os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5"),
                max_tokens=1000,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime,
                                                 "data": base64.b64encode(imagen).decode()}},
                    {"type": "text", "text": PROMPT},
                ]}],
            )
            texto = msg.content[0].text
            datos = json.loads(texto[texto.index("{"): texto.rindex("}") + 1])
            meds = [m for m in datos.get("medicamentos", []) if m.get("nombre")]
            if meds:
                return {"origen": "ia", "medicamentos": [
                    {"nombre": m["nombre"], "dosis_mg": m.get("dosis_mg") or 0,
                     "cada_horas": m.get("cada_horas") or 24, "dias": m.get("dias") or 30}
                    for m in meds]}
        except Exception as e:  # noqa: BLE001 - en demo preferimos caer al ejemplo
            print("[ai.py] No se pudo leer la receta con IA:", e)
    return {"origen": "simulado", "medicamentos": EJEMPLO}
