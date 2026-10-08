"""Suscripción de abastecimiento automático: cuando una medicina entra en el margen de días de la
suscripción, se pide sola a domicilio a Farmaenlace.

Reglas:
- Pide un mes de tratamiento de cada medicina con dias_restantes <= dias_anticipacion
  (no si el IESS aún no responde: puede que entregue).
- No pide lo que ya tiene un pedido abierto, ni repite el mismo día lo que Farmaenlace rechazó.
- Controlados: no van por delivery (requieren retiro con receta especial); se registra y se omiten.
- Sin consentimiento del paciente no se comparten sus datos: no hay pedido.
- Reparto entre sucursales: cada medicina va a la preferida si alcanza; si no, a la sucursal con stock
  completo más conveniente (agrupando para hacer pocos pedidos). Si nadie la tiene completa, se pide
  lo máximo disponible en una sucursal (pedido parcial).
"""
import uuid

import db
from abastecimiento import eventos, farmacias, pedidos
from abastecimiento import repositorio as repo


def obtener(paciente_id):
    return db._uno("SELECT * FROM suscripcion WHERE paciente_id = %s", paciente_id)


def activar(paciente_id, dias_anticipacion=7, uid_farmacia_preferida=None):
    db._c().execute("""
        INSERT INTO suscripcion (paciente_id, activa, dias_anticipacion, uid_farmacia_preferida)
        VALUES (%s, TRUE, %s, %s)
        ON CONFLICT (paciente_id) DO UPDATE SET activa = TRUE, dias_anticipacion = EXCLUDED.dias_anticipacion,
            uid_farmacia_preferida = EXCLUDED.uid_farmacia_preferida, actualizada_en = now()""",
        (paciente_id, dias_anticipacion, uid_farmacia_preferida))
    return obtener(paciente_id)


def desactivar(paciente_id):
    db._c().execute("UPDATE suscripcion SET activa = FALSE, actualizada_en = now() WHERE paciente_id = %s",
                    (paciente_id,))
    return obtener(paciente_id)


def _log(tipo, paciente_id, **datos):
    eventos.registrar(str(uuid.uuid4()), "interno", tipo, {"paciente_id": paciente_id, **datos})


def repartir(paciente, cuidadores, necesidades, preferida=None):
    """necesidades: [{"uid_medicina", "cantidad", ...}] -> {uid_farmacia: [items]} (items con su cantidad final)."""
    sugeridas = farmacias.sugerir(paciente, cuidadores, necesidades, maximo=50)
    stock = {f["id"]: {i["uid_medicina"]: i["disponible"] for i in f["items"]} for f in sugeridas}
    orden = [f["id"] for f in sugeridas]          # mejor cobertura y más cerca primero
    if preferida in stock:
        orden.remove(preferida)
        orden.insert(0, preferida)
    asignacion = {}
    for n in necesidades:
        uid, cantidad = n["uid_medicina"], n["cantidad"]
        # 1) una sucursal ya elegida que lo tenga completo, 2) la primera del orden que lo tenga completo
        elegida = next((f for f in list(asignacion) + orden if stock[f].get(uid, 0) >= cantidad), None)
        if elegida is None:   # nadie lo tiene completo: lo máximo disponible (pedido parcial)
            elegida = max(orden, key=lambda f: stock[f].get(uid, 0), default=None)
            if elegida is None or stock[elegida].get(uid, 0) == 0:
                continue
            cantidad = stock[elegida][uid]
        stock[elegida][uid] -= cantidad
        asignacion.setdefault(elegida, []).append({**n, "cantidad": cantidad, "parcial": cantidad < n["cantidad"]})
    return asignacion


def procesar(paciente_id, filas):
    """Llamado por el evaluador. filas = v_saldo_medicacion del paciente. Devuelve los pedidos creados."""
    s = obtener(paciente_id)
    if not s or not s["activa"]:
        return []
    candidatos = [f for f in filas if f["estado"] in ("por_agotarse", "agotado")
                  and f["dias_restantes"] <= s["dias_anticipacion"]]
    if not candidatos:
        return []
    hoy = repo.fecha_referencia()
    excluir = pedidos.uids_abiertos(paciente_id) | pedidos.uids_rechazados(paciente_id, hoy)
    candidatos = [f for f in candidatos if f["uid_medicina"] not in excluir]
    controlados = [f["nombre"] for f in candidatos if f["controlado"]]
    if controlados:
        _log("SuscripcionRequiereRetiro", paciente_id, medicinas=controlados,
             motivo="requiere retiro presencial con receta especial")
    candidatos = [f for f in candidatos if not f["controlado"]]
    if not candidatos:
        return []
    paciente = db._uno("""SELECT id, nombre, lat::float AS lat, lng::float AS lng, consentimiento
                          FROM paciente WHERE id = %s""", paciente_id)
    if not paciente["consentimiento"]:
        _log("SuscripcionOmitida", paciente_id, motivo="sin consentimiento para compartir datos con la farmacia")
        return []
    necesidades = [{"uid_medicina": f["uid_medicina"], "receta_item_id": f["receta_item_id"],
                    "cantidad": f["tomas_por_dia"] * f["dias_receta"]} for f in candidatos]
    reparto = repartir(paciente, repo.cuidadores_de(paciente_id), necesidades, s["uid_farmacia_preferida"])
    sin_stock = {n["uid_medicina"] for n in necesidades} - {i["uid_medicina"] for its in reparto.values() for i in its}
    if sin_stock:
        _log("SuscripcionSinStock", paciente_id, medicinas=sorted(sin_stock))
    parciales = [{"uid_medicina": i["uid_medicina"], "farmacia": f, "pedido": i["cantidad"],
                  "necesario": next(n["cantidad"] for n in necesidades if n["uid_medicina"] == i["uid_medicina"])}
                 for f, its in reparto.items() for i in its if i["parcial"]]
    if parciales:   # ninguna sucursal tenía el mes completo: se pidió lo máximo disponible
        _log("SuscripcionParcial", paciente_id, items=parciales)
    creados = []
    for uid_farmacia, items in reparto.items():
        try:
            creados.append(pedidos.crear(paciente_id, uid_farmacia, "delivery", items, origen="suscripcion"))
        except pedidos.PedidoInvalido as e:
            _log("SuscripcionOmitida", paciente_id, motivo=str(e))
    return creados
