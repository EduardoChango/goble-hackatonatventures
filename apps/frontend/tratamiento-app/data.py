"""Datos simulados y almacenamiento del estado.

EDU: este archivo es el punto de enganche para datos reales.
- FARMACIAS: reemplazar por la API o base de datos de Farmaenlace (stock real).
- Con DATABASE_URL el estado vive en PostgreSQL (db.py); sin ella, en data/state.json.
  Ver la sección "Almacenamiento" al final.
"""
import json
import os
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "data", "state.json")

# Ubicación por defecto: La Palma Polo Club (sede del hackatón, Puembo, Quito).
CENTRO = (-0.1588, -78.3665)

# FARMACIAS REALES del grupo Farmaenlace (Farmacias Económicas y Medicity) cerca de Puembo.
# Nombres, direcciones, horarios y coordenadas salen de Google Maps (pueden cambiar).
# El STOCK es SIMULADO: las cantidades son inventadas. EDU: aquí se conectaría el stock real.

# Promociones de ejemplo (simuladas). EDU: aqui se conectaria el servicio real de promociones de Farmaenlace.
PROMOS = [
    {"titulo": "15% de descuento en Metformina", "detalle": "Tratamientos de 30 días o más. Con tarjeta de fidelidad.", "med": "Metformina", "vence": "Hoy"},
    {"titulo": "2x1 en tiras reactivas de glucosa", "detalle": "Para controlar la diabetes en casa.", "med": None, "vence": "Hasta el domingo"},
    {"titulo": "10% en tensiómetros digitales", "detalle": "Para medir la presión en casa.", "med": "Losartán", "vence": "Esta semana"},
    {"titulo": "Envío gratis desde $15", "detalle": "En pedidos de medicinas de tratamiento crónico.", "med": None, "vence": "Hoy"},
]

FARMACIAS = [
    {"id": 1, "nombre": "Medicity · Puembo", "parroquia": "Puembo", "direccion": "Manuel Burbano",
     "lat": -0.1774634, "lng": -78.3588022, "horario": "Abierta hasta las 20:30",
     "stock": {"Losartán": 80, "Metformina": 100, "Atorvastatina": 60, "Amlodipino": 25}},
    {"id": 2, "nombre": "Económicas · Puembo Centro", "parroquia": "Puembo", "direccion": "Simón Bolívar y 24 de Mayo",
     "lat": -0.1786097, "lng": -78.358901, "horario": "Abierta hasta las 20:00",
     "stock": {"Losartán": 30, "Metformina": 55, "Atorvastatina": 0, "Amlodipino": 18}},
    {"id": 3, "nombre": "Económicas · Puembo", "parroquia": "Puembo", "direccion": "24 de Mayo y Humberto Duque",
     "lat": -0.1984982, "lng": -78.3680239, "horario": "Abierta hasta las 20:00",
     "stock": {"Losartán": 0, "Metformina": 22, "Atorvastatina": 30, "Amlodipino": 0}},
    {"id": 4, "nombre": "Medicity · Puembo 24 de Mayo", "parroquia": "Puembo", "direccion": "24 de Mayo y Patricio Romero",
     "lat": -0.1998237, "lng": -78.3676522, "horario": "Abierta hasta las 21:30",
     "stock": {"Losartán": 45, "Metformina": 8, "Atorvastatina": 20, "Amlodipino": 40}},
    {"id": 5, "nombre": "Económicas · Yaruquí", "parroquia": "Yaruquí", "direccion": "Av. Amazonas",
     "lat": -0.1624381, "lng": -78.3200072, "horario": "Abierta hasta las 21:00",
     "stock": {"Losartán": 20, "Metformina": 36, "Atorvastatina": 6, "Amlodipino": 12}},
    {"id": 6, "nombre": "Medicity · Vía Pifo", "parroquia": "Puembo / Tumbaco", "direccion": "Av. Guayasamín y Ruta Viva",
     "lat": -0.2105018, "lng": -78.3643521, "horario": "Abierta hasta las 21:00",
     "stock": {"Losartán": 12, "Metformina": 0, "Atorvastatina": 0, "Amlodipino": 9}},
    {"id": 7, "nombre": "Económicas · Tumbaco Villavega", "parroquia": "Tumbaco", "direccion": "Villa Vega y Av. Guayasamín",
     "lat": -0.209798, "lng": -78.3868623, "horario": "Abierta hasta las 21:00",
     "stock": {"Losartán": 70, "Metformina": 64, "Atorvastatina": 48, "Amlodipino": 33}},
    {"id": 8, "nombre": "Económicas · Pifo Chaupimolino", "parroquia": "Pifo", "direccion": "Chaupimolino",
     "lat": -0.2196237, "lng": -78.3388996, "horario": "Abierta hasta las 21:00",
     "stock": {"Losartán": 18, "Metformina": 14, "Atorvastatina": 10, "Amlodipino": 7}},
    {"id": 9, "nombre": "Medicity · Tumbaco Central", "parroquia": "Tumbaco", "direccion": "Juan Montalvo y Fray Gonzalo de Vera",
     "lat": -0.213573, "lng": -78.4056652, "horario": "Abierta hasta las 21:00",
     "stock": {"Losartán": 26, "Metformina": 31, "Atorvastatina": 0, "Amlodipino": 15}},
    {"id": 10, "nombre": "Medicity · Tumbaco La Cerámica", "parroquia": "Tumbaco", "direccion": "La Cerámica",
     "lat": -0.2211377, "lng": -78.3929391, "horario": "Abierta hasta las 21:00",
     "stock": {"Losartán": 50, "Metformina": 50, "Atorvastatina": 25, "Amlodipino": 20}},
    {"id": 11, "nombre": "Económicas · Pifo Gonzalo Pizarro", "parroquia": "Pifo", "direccion": "Gonzalo Pizarro",
     "lat": -0.2242182, "lng": -78.3407142, "horario": "Abierta hasta las 21:00",
     "stock": {"Losartán": 35, "Metformina": 25, "Atorvastatina": 15, "Amlodipino": 10}},
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


# ---------------------------------------------------------------------------
# Almacenamiento. Dos modos con la misma interfaz:
# - Con DATABASE_URL (local con Docker) o DB_HOST (AWS) -> PostgreSQL, ver db.py y db/init/.
#   Cada usuario del login ve solo su paciente; FARMACIAS y PROMOS se leen de la BD.
# - Sin esas variables -> data/state.json con un solo paciente (Luis Mora), como antes.
# app.py modifica el dict `s` y luego llama a la función de guardado que corresponde
# (guardar_perfil, registrar_compra, ...). En modo JSON todas equivalen a save().
# ---------------------------------------------------------------------------
USAR_BD = bool(os.getenv("DATABASE_URL") or os.getenv("DB_HOST"))
DEMO_EMAIL, DEMO_PASSWORD = "luis.mora@demo.ec", "demo1234"  # login del modo JSON

if USAR_BD:
    import db

_STATE = None


def load():
    global _STATE
    if USAR_BD:
        s, farmacias, promos = db.cargar()
        FARMACIAS[:] = farmacias  # logic.py importa esta misma lista
        PROMOS[:] = promos
        return s
    if _STATE is None:
        if os.path.exists(PATH):
            with open(PATH, encoding="utf-8") as f:
                _STATE = json.load(f)
        else:
            _STATE = seed()
            save()
    return _STATE


def save():
    if USAR_BD:
        return
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(_STATE, f, ensure_ascii=False, indent=2)


def reset():
    global _STATE
    if USAR_BD:
        return db.reset()
    _STATE = seed()
    save()
    return _STATE


# ---------- sesión ----------
def autenticar(email, password):
    """Devuelve el id del paciente si las credenciales son válidas."""
    if USAR_BD:
        return db.autenticar(email, password)
    ok = email.strip().lower() == DEMO_EMAIL and password == DEMO_PASSWORD
    return 1 if ok else None


def usuarios_demo():
    """[(email, nombre del paciente)] para mostrar en la pantalla de login."""
    return db.usuarios_demo() if USAR_BD else [(DEMO_EMAIL, seed()["perfil"]["nombre"])]


def usar_paciente(pid):
    if USAR_BD:
        db.usar_paciente(pid)


def cerrar():
    if USAR_BD:
        db.cerrar()


# ---------- guardado ----------
# Cambios que alteran cuánta medicación tiene el paciente: el evaluador lo revisa al instante
_REEVALUAR = {"guardar_receta", "registrar_entrega", "registrar_compra"}


def _guardar(funcion, *args):
    if USAR_BD:
        getattr(db, funcion)(*args)
        if funcion in _REEVALUAR:
            from abastecimiento import eventos  # import diferido: eventos importa db
            eventos.publicar("PacienteActualizado", {"paciente_id": db._pid(), "motivo": funcion})
    else:
        save()


def guardar_perfil(perfil):
    _guardar("guardar_perfil", perfil)


def guardar_ubicacion(lat, lng):
    _guardar("guardar_ubicacion", lat, lng)


def guardar_receta(fecha, meds, origen="manual", extraccion=None):
    _guardar("guardar_receta", fecha, meds, origen, extraccion)


def registrar_entrega(fecha, registro):
    _guardar("registrar_entrega", fecha, registro)


def registrar_compra(farmacia_id, modo, unidades):
    _guardar("registrar_compra", farmacia_id, modo, unidades)


def registrar_toma(did):
    _guardar("registrar_toma", did)


def guardar_avisos(avisos, claves_nuevas):
    _guardar("guardar_avisos", avisos, claves_nuevas)


def encolar_aviso(aviso):
    _guardar("encolar_aviso", aviso)
