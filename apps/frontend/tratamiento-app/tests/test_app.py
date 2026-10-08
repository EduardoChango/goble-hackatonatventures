"""Pruebas de punta a punta de la app con Flask test client.

- Con DATABASE_URL (Postgres de db/docker-compose.yml): prueba login, aislamiento entre
  usuarios y cada escritura contra la BD. Al final restablece los datos del paciente.
- Sin DATABASE_URL: prueba el modo JSON (data/state.json).

Correr desde apps/frontend/tratamiento-app:
    DATABASE_URL=postgresql://goble:goble@localhost:5432/tratamiento python -m pytest tests -v
    python -m pytest tests -v
"""
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as app_module  # noqa: E402
import data  # noqa: E402

BD = data.USAR_BD


@pytest.fixture
def client(tmp_path, monkeypatch):
    if not BD:
        monkeypatch.setattr(data, "PATH", str(tmp_path / "state.json"))
        monkeypatch.setattr(data, "_STATE", None)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def entrar(client, email="luis.mora@demo.ec", password="demo1234"):
    return client.post("/login", data={"email": email, "password": password})


def stock(farmacia_id, med):
    import db
    c = db.conectar()
    try:
        return c.execute("""SELECT s.unidades FROM farmacia_stock s JOIN medicamento m ON m.id = s.medicamento_id
                            WHERE s.farmacia_id = %s AND m.nombre_generico = %s""", (farmacia_id, med)).fetchone()["unidades"]
    finally:
        c.close()


def faltantes(paciente_id):
    import db
    c = db.conectar()
    try:
        return [r["nombre"] for r in c.execute(
            "SELECT nombre FROM v_faltantes WHERE paciente_id = %s ORDER BY nombre", (paciente_id,))]
    finally:
        c.close()


def test_sin_login_redirige_y_api_da_401(client):
    assert client.get("/").headers["Location"].endswith("/login")
    assert client.get("/api/avisos").status_code == 401
    assert client.get("/login").status_code == 200
    assert client.get("/static/css/app.css").status_code == 200
    assert client.get("/sw.js").status_code == 200


def test_login_incorrecto(client):
    r = entrar(client, password="mala")
    assert r.status_code == 200 and "incorrectos" in r.get_data(as_text=True)


def test_paginas_con_login(client):
    assert entrar(client).headers["Location"] == "/"
    for ruta in ["/", "/perfil", "/receta", "/receta?nueva=1", "/entrega", "/plan", "/farmacias", "/resumen"]:
        r = client.get(ruta)
        assert r.status_code == 200, ruta
    html = client.get("/").get_data(as_text=True)
    assert "Luis Mora" in html and "2 de 4" in html  # 2 de 4 dosis tomadas hoy (seed)
    assert client.get("/logout").headers["Location"].endswith("/login")
    assert client.get("/").status_code == 302


@pytest.mark.skipif(not BD, reason="requiere DATABASE_URL")
def test_cada_usuario_ve_solo_su_paciente(client):
    entrar(client, "carmen.pazmino@demo.ec")
    html = client.get("/").get_data(as_text=True)
    assert "Carmen Pazmiño" in html and "Luis Mora" not in html
    assert "Sin IESS" in html


@pytest.mark.skipif(not BD, reason="requiere DATABASE_URL")
def test_flujo_completo_y_reset(client):
    entrar(client)
    # Farmacias muestra los faltantes de la BD (Metformina 32, Atorvastatina 30)
    html = client.get("/farmacias").get_data(as_text=True)
    assert "Medicity · Puembo" in html or "Económicas" in html

    # Perfil
    client.post("/perfil", data={"nombre": "Luis Mora (ejemplo)", "edad": "73", "cuidador": "Nieta",
                                 "condiciones": "Hipertensión, Diabetes tipo 2, Gota", "iess": "si",
                                 "consentimiento": "on", "cita": "2026-11-20T09:30"})
    html = client.get("/").get_data(as_text=True)
    assert "73 años" in html and "Nieta" in html and "Gota" in html

    # Tomar una dosis
    client.post("/plan/tomar", data={"id": "Metformina@20:00", "volver": "/plan"})
    assert "3 de 4" in client.get("/").get_data(as_text=True)

    # Comprar en la farmacia 1 descuenta stock y elimina los faltantes
    antes = stock(1, "Metformina")
    client.post("/farmacias/comprar", data={"farmacia": "1", "modo": "envio"})
    assert stock(1, "Metformina") == antes - 32
    assert faltantes(1) == []

    # Avisos: simular las 21:00 genera el aviso de Atorvastatina 21:00 una sola vez
    client.post("/api/simular", json={"accion": "hora", "hora": "21:00"})
    primeros = client.get("/api/avisos").get_json()["avisos"]
    assert any("Atorvastatina" in a["cuerpo"] for a in primeros)
    assert client.get("/api/avisos").get_json()["avisos"] == []  # no se repite
    client.post("/api/simular", json={"accion": "aviso", "tipo": "cita"})
    assert client.get("/api/avisos").get_json()["avisos"][0]["tipo"] == "cita"

    # Nueva receta (manual) para hoy y registro de entrega
    client.post("/receta/confirmar", data={"nombre": ["Losartán", "Enalapril"], "dosis_mg": ["100", "10"],
                                            "cada_horas": ["24", "12"], "dias": ["30", "30"]})
    html = client.get("/receta").get_data(as_text=True)
    assert "Enalapril" in html
    client.post("/entrega", data={"estado_0": "completo", "estado_1": "parcial", "recibido_1": "20"})
    assert "Enalapril" in client.get("/farmacias").get_data(as_text=True)

    # Restablecer: vuelve al estado de ejemplo y repone el stock
    client.post("/api/simular", json={"accion": "reset"})
    html = client.get("/").get_data(as_text=True)
    assert "72 años" in html and "2 de 4" in html and "Nieta" not in html
    assert stock(1, "Metformina") == antes
    # el login sigue funcionando después del reset (el usuario se vuelve a crear)
    client.get("/logout")
    assert entrar(client).headers["Location"] == "/"


def test_receta_ia_simulada_sin_credenciales(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    entrar(client)
    r = client.post("/receta/leer", data={}, content_type="multipart/form-data")
    assert r.status_code == 200 and re.search("ejemplo|simulad", r.get_data(as_text=True), re.I)
