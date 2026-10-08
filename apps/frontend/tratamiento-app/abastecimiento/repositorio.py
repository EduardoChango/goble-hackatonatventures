"""Consultas del módulo de abastecimiento sobre PostgreSQL (usa la conexión por request de db.py)."""
from datetime import date, timedelta

import db

# ---------- reloj de la demo (config_demo.fecha_referencia) ----------


def fecha_referencia():
    return db._uno("SELECT fecha_referencia() AS f")["f"]


def fijar_fecha_referencia(fecha):
    """fecha=None vuelve a la fecha real."""
    if fecha is None:
        db._c().execute("DELETE FROM config_demo WHERE clave = 'fecha_referencia'")
    else:
        db._c().execute("""INSERT INTO config_demo (clave, valor) VALUES ('fecha_referencia', %s)
                           ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor""", (fecha.isoformat(),))
    return fecha_referencia()


def avanzar_dias(n):
    return fijar_fecha_referencia(fecha_referencia() + timedelta(days=int(n)))


def reloj_simulado():
    """True si la demo no está en la fecha real."""
    return fecha_referencia() != date.today()


# ---------- saldo de medicación ----------


def saldos(paciente_id=None):
    """Filas de v_saldo_medicacion (receta vigente); de un paciente o de todos."""
    filtro, params = ("WHERE paciente_id = %s", (paciente_id,)) if paciente_id is not None else ("", ())
    return db._todos(f"""
        SELECT paciente_id, receta_item_id, nombre, dosis_mg, uid_medicina, concentracion, grupo, controlado,
               tomas_por_dia, dias_receta, inicio, fin_tratamiento, recibido_iess, comprado,
               unidades_obtenidas, saldo_unidades, fecha_agotamiento, dias_restantes, umbral_dias,
               fecha_referencia, estado
        FROM v_saldo_medicacion {filtro}
        ORDER BY paciente_id, dias_restantes, nombre""", *params)


# ---------- cuidadores ----------


def cuidadores_de(paciente_id):
    return db._todos("""
        SELECT c.id, c.nombre, c.email, c.telefono, c.lat::float AS lat, c.lng::float AS lng, pc.rol, pc.parentesco
        FROM paciente_cuidador pc JOIN cuidador c ON c.id = pc.cuidador_id
        WHERE pc.paciente_id = %s ORDER BY pc.rol DESC, c.nombre""", paciente_id)


def pacientes_de(cuidador_id):
    return db._todos("""
        SELECT p.id, p.nombre, pc.rol, pc.parentesco, p.movilidad_reducida
        FROM paciente_cuidador pc JOIN paciente p ON p.id = pc.paciente_id
        WHERE pc.cuidador_id = %s ORDER BY p.nombre""", cuidador_id)


# ---------- productos relacionados ----------


def sugerencias(paciente_id):
    """Productos por las condiciones del paciente o por el grupo de sus medicinas actuales."""
    return db._todos("""
        SELECT DISTINCT ON (pr.id) pr.id, pr.nombre, pr.categoria, pr.presentacion, rs.motivo
        FROM regla_sugerencia rs
        JOIN producto pr ON pr.id = rs.producto_id
        WHERE rs.condicion_id IN (SELECT condicion_id FROM paciente_condicion WHERE paciente_id = %s)
           OR rs.grupo_medicina IN (SELECT grupo FROM v_saldo_medicacion WHERE paciente_id = %s)
        ORDER BY pr.id, rs.id""", paciente_id, paciente_id)
