"""Datos simulados y almacenamiento del estado.

EDU: este archivo es el punto de enganche para datos reales.
- FARMACIAS: reemplazar por la API o base de datos de Farmaenlace (stock real).
- El estado completo (perfil, visitas, entregas, compras, tomas) vive en data/state.json.
  Si prefieren SQL, cambien load() y save() y dejen el resto igual.
"""
import json
import os
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "data", "state.json")

# Ubicación por defecto: centro de Ambato (aproximada). Todo lo demás es inventado.
CENTRO = (-1.2491, -78.6167)

# STOCK SIMULADO. Las coordenadas son aproximadas y las cantidades son inventadas.
# Promociones de ejemplo (simuladas). EDU: aqui se conectaria el servicio real de promociones de Farmaenlace.
PROMOS = [
    {"titulo": "15% de descuento en Metformina", "detalle": "Tratamientos de 30 días o más. Con tarjeta de fidelidad.", "med": "Metformina", "vence": "Hoy"},
    {"titulo": "2x1 en tiras reactivas de glucosa", "detalle": "Para controlar la diabetes en casa.", "med": None, "vence": "Hasta el domingo"},
    {"titulo": "10% en tensiómetros digitales", "detalle": "Para medir la presión en casa.", "med": "Losartán", "vence": "Esta semana"},
    {"titulo": "Envío gratis desde $15", "detalle": "En pedidos de medicinas de tratamiento crónico.", "med": None, "vence": "Hoy"},
]

FARMACIAS = [
    {"id": 1, "nombre": "Económicas · Centro", "lat": -1.2519, "lng": -78.6167, "horario": "Abierta hasta las 21:00",
     "stock": {"Losartán": 60, "Metformina": 40, "Atorvastatina": 30, "Amlodipino": 25}},
    {"id": 2, "nombre": "Medicity · Centro Comercial", "lat": -1.2441, "lng": -78.6102, "horario": "Abierta hasta las 22:00",
     "stock": {"Losartán": 30, "Metformina": 22, "Atorvastatina": 0, "Amlodipino": 18}},
    {"id": 3, "nombre": "Económicas · Ficoa", "lat": -1.2334, "lng": -78.6230, "horario": "Abierta hasta las 20:00",
     "stock": {"Losartán": 0, "Metformina": 55, "Atorvastatina": 30, "Amlodipino": 0}},
    {"id": 4, "nombre": "Económicas · Terminal", "lat": -1.2572, "lng": -78.6089, "horario": "Abierta hasta las 21:00",
     "stock": {"Losartán": 45, "Metformina": 8, "Atorvastatina": 20, "Amlodipino": 40}},
    {"id": 5, "nombre": "Medicity · Huachi", "lat": -1.2685, "lng": -78.6270, "horario": "Abierta hasta las 21:30",
     "stock": {"Losartán": 20, "Metformina": 36, "Atorvastatina": 6, "Amlodipino": 12}},
    {"id": 6, "nombre": "Económicas · Atocha", "lat": -1.2296, "lng": -78.6341, "horario": "Abierta hasta las 20:00",
     "stock": {"Losartán": 12, "Metformina": 0, "Atorvastatina": 0, "Amlodipino": 9}},
    {"id": 7, "nombre": "Económicas · Pishilata", "lat": -1.2630, "lng": -78.5990, "horario": "Abierta hasta las 21:00",
     "stock": {"Losartán": 70, "Metformina": 64, "Atorvastatina": 48, "Amlodipino": 33}},
    {"id": 8, "nombre": "Medicity · Ingahurco", "lat": -1.2380, "lng": -78.6130, "horario": "Abierta hasta las 22:00",
     "stock": {"Losartán": 18, "Metformina": 14, "Atorvastatina": 10, "Amlodipino": 7}},
    {"id": 9, "nombre": "Económicas · Miraflores", "lat": -1.2450, "lng": -78.6240, "horario": "Abierta hasta las 20:30",
     "stock": {"Losartán": 26, "Metformina": 31, "Atorvastatina": 0, "Amlodipino": 15}},
    {"id": 10, "nombre": "Económicas · Izamba", "lat": -1.2040, "lng": -78.5780, "horario": "Abierta hasta las 20:00",
     "stock": {"Losartán": 50, "Metformina": 50, "Atorvastatina": 25, "Amlodipino": 20}},
]


def seed():
    """Estado inicial de la demo: el mismo caso del mockup (paciente de ejemplo)."""
    hoy = date.today().isoformat()
    return {
        "perfil": {
            "nombre": "Luis Mora (ejemplo)", "edad": 72, "cuidador": "Hijo/a",
            "condiciones": ["Hipertensión", "Diabetes tipo 2"],
            "iess": True, "consentimiento": True,
            "lat": CENTRO[0], "lng": CENTRO[1],
            "cita": "2026-10-17T10:00",
        },
        "visitas": [
            {"fecha": "2026-09-12", "meds": [
                {"nombre": "Losartán", "dosis_mg": 50, "cada_horas": 24, "dias": 30, "horarios": ["08:00"]},
                {"nombre": "Metformina", "dosis_mg": 850, "cada_horas": 12, "dias": 30, "horarios": ["08:00", "20:00"]},
            ]},
            {"fecha": "2026-10-03", "meds": [
                {"nombre": "Losartán", "dosis_mg": 100, "cada_horas": 24, "dias": 30, "horarios": ["08:00"]},
                {"nombre": "Metformina", "dosis_mg": 850, "cada_horas": 12, "dias": 30, "horarios": ["08:00", "20:00"]},
                {"nombre": "Atorvastatina", "dosis_mg": 20, "cada_horas": 24, "dias": 30, "horarios": ["21:00"]},
            ]},
        ],
        # Qué entregó el IESS por visita: completo | parcial | no
        "entregas": {
            "2026-10-03": {
                "Losartán": {"estado": "completo", "recibido": 30},
                "Metformina": {"estado": "parcial", "recibido": 28},
                "Atorvastatina": {"estado": "no", "recibido": 0},
            }
        },
        "compras": {},                                  # unidades compradas por visita
        "vendido": {},                                  # stock simulado ya vendido en la demo, por farmacia
        "tomas": {hoy: ["Losartán@08:00", "Metformina@08:00"]},
        "enviados": [],                                 # avisos ya mostrados (para no repetir)
        "cola": [],                                     # avisos manuales del panel Demo
        "sim_hora": None,                               # hora simulada (HH:MM) o None = hora real
    }


_STATE = None


def load():
    global _STATE
    if _STATE is None:
        if os.path.exists(PATH):
            with open(PATH, encoding="utf-8") as f:
                _STATE = json.load(f)
        else:
            _STATE = seed()
            save()
    return _STATE


def save():
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(_STATE, f, ensure_ascii=False, indent=2)


def reset():
    global _STATE
    _STATE = seed()
    save()
    return _STATE
