"""Farmacias de Farmaenlace sugeridas para lo que le falta a un paciente.

Orden: 1) cuántos de los medicamentos pedidos tiene en stock suficiente (cobertura),
2) distancia mínima al paciente (delivery) o a alguno de sus cuidadores (retiro).
"""
import db
import logic


def stock_para(uids):
    """{uid_farmacia: {"farmacia": {...}, "stock": {uid_medicina: cantidad}}} para las medicinas dadas."""
    farmacias = {}
    for r in db._todos("""
            SELECT f.uid, f.nombre, f.direccion, f.lat, f.long AS lng, f.horario, s.uid_medicina, s.cantidad
            FROM farmacias f
            LEFT JOIN stock s ON s.uid_farmacia = f.uid AND s.uid_medicina = ANY(%s::text[])
            ORDER BY f.uid""", list(uids)):
        f = farmacias.setdefault(r["uid"], {
            "farmacia": {"id": r["uid"], "nombre": r["nombre"], "direccion": r["direccion"],
                         "lat": r["lat"], "lng": r["lng"], "horario": r["horario"]},
            "stock": {}})
        if r["uid_medicina"]:
            f["stock"][r["uid_medicina"]] = r["cantidad"]
    return farmacias


def sugerir(paciente, cuidadores, pedidos, maximo=3):
    """
    paciente:   {"lat", "lng"}           cuidadores: [{"nombre", "lat", "lng"}, ...]
    pedidos:    [{"uid_medicina", "cantidad"}]  (lo que se necesita)
    Devuelve las mejores farmacias con su cobertura y desde dónde queda más cerca.
    """
    if not pedidos:
        return []
    puntos = [("paciente", paciente["lat"], paciente["lng"])] + [
        (c["nombre"], c["lat"], c["lng"]) for c in cuidadores]
    sugeridas = []
    for f in stock_para(p["uid_medicina"] for p in pedidos).values():
        far = f["farmacia"]
        desde, dist = min(((n, logic.km(la, lo, far["lat"], far["lng"])) for n, la, lo in puntos),
                          key=lambda x: x[1])
        items = [{"uid_medicina": p["uid_medicina"], "necesita": p["cantidad"],
                  "disponible": f["stock"].get(p["uid_medicina"], 0)} for p in pedidos]
        cubre = sum(i["disponible"] >= i["necesita"] for i in items)
        if not any(i["disponible"] for i in items):
            continue
        sugeridas.append({**far, "km": round(dist, 1), "mas_cerca_de": desde, "cubre": cubre,
                          "completa": cubre == len(items), "items": items})
    sugeridas.sort(key=lambda f: (-f["cubre"], f["km"]))
    return sugeridas[:maximo]
