"""Reglas de negocio: comparar recetas, inventario, faltantes, dosis del día, avisos y farmacias cercanas.

Supuestos de la demo (decirlo en el pitch):
- 1 tableta por toma.
- Los días restantes se estiman con lo que se recibió o compró para la receta actual.
- La app solo registra lo que dice la receta: nunca sugiere ni cambia dosis.
"""
from datetime import date, datetime, timedelta
from math import asin, cos, radians, sin, sqrt

from data import FARMACIAS

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_L = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
           "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

HORARIOS_POR_DEFECTO = {24: ["08:00"], 12: ["08:00", "20:00"], 8: ["06:00", "14:00", "22:00"],
                        6: ["06:00", "12:00", "18:00", "00:00"]}

ETIQUETAS = {
    "nuevo": "Medicamento nuevo", "aumentada": "Dosis aumentada", "reducida": "Dosis reducida",
    "frecuencia": "Frecuencia cambiada", "igual": "Sin cambios", "primera": "Primera visita",
    "suspendido": "Ya no está en la receta",
}


# ---------- fechas ----------
def fecha_corta(iso):
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {MESES[d.month - 1]}"


def fecha_larga(iso):
    d = date.fromisoformat(iso[:10])
    return f"{DIAS[d.weekday()]} {d.day} de {MESES_L[d.month - 1]}"


def hoy_iso():
    return date.today().isoformat()


def ahora(s):
    return s.get("sim_hora") or datetime.now().strftime("%H:%M")


# ---------- receta ----------
def horarios_de(med):
    return med.get("horarios") or HORARIOS_POR_DEFECTO.get(int(med["cada_horas"]), ["08:00"])


def tomas_por_dia(med):
    return len(horarios_de(med))


def total_recetado(med):
    return tomas_por_dia(med) * int(med["dias"])


def visita_actual(s):
    return max(s["visitas"], key=lambda v: v["fecha"]) if s["visitas"] else None


def visita_previa(s, fecha):
    previas = [v for v in s["visitas"] if v["fecha"] < fecha]
    return max(previas, key=lambda v: v["fecha"]) if previas else None


def comparar(actual, previa):
    """Cada medicamento de la visita con su estado frente a la visita anterior."""
    filas = []
    previos = {m["nombre"].lower(): m for m in (previa["meds"] if previa else [])}
    for m in actual["meds"]:
        p = previos.pop(m["nombre"].lower(), None)
        fila = dict(m)
        if not previa:
            fila.update(estado="primera", detalle=f'{m["dosis_mg"]} mg')
        elif p is None:
            fila.update(estado="nuevo", detalle=f'{m["dosis_mg"]} mg')
        elif int(m["dosis_mg"]) > int(p["dosis_mg"]):
            fila.update(estado="aumentada", detalle=f'{p["dosis_mg"]} mg → {m["dosis_mg"]} mg')
        elif int(m["dosis_mg"]) < int(p["dosis_mg"]):
            fila.update(estado="reducida", detalle=f'{p["dosis_mg"]} mg → {m["dosis_mg"]} mg')
        elif int(m["cada_horas"]) != int(p["cada_horas"]):
            fila.update(estado="frecuencia", detalle=f'{m["dosis_mg"]} mg · antes cada {p["cada_horas"]} h')
        else:
            fila.update(estado="igual", detalle=f'{m["dosis_mg"]} mg')
        filas.append(fila)
    for p in previos.values():  # estaba antes y ya no
        fila = dict(p)
        fila.update(estado="suspendido", detalle=f'{p["dosis_mg"]} mg')
        filas.append(fila)
    return filas


# ---------- entrega del IESS, compras e inventario ----------
def entrega_de(s, fecha, nombre):
    return s["entregas"].get(fecha, {}).get(nombre)


def comprado(s, fecha, nombre):
    return int(s["compras"].get(fecha, {}).get(nombre, 0))


def recibido_iess(s, fecha, nombre):
    if not s["perfil"].get("iess"):
        return 0
    e = entrega_de(s, fecha, nombre)
    return int(e["recibido"]) if e and e["estado"] != "no" else 0


def inventario(s, med, fecha):
    return recibido_iess(s, fecha, med["nombre"]) + comprado(s, fecha, med["nombre"])


def falta_respuesta_iess(s):
    v = visita_actual(s)
    return bool(s["perfil"].get("iess") and v and v["fecha"] not in s["entregas"])


def faltantes(s):
    v = visita_actual(s)
    if not v or falta_respuesta_iess(s):
        return []
    salida = []
    for m in v["meds"]:
        total = total_recetado(m)
        falta = total - inventario(s, m, v["fecha"])
        if falta <= 0:
            continue
        e = entrega_de(s, v["fecha"], m["nombre"])
        if not s["perfil"].get("iess"):
            motivo = "Sin IESS: se compra todo"
        elif e and e["estado"] == "no":
            motivo = "Sin stock en el IESS"
        else:
            motivo = f'El IESS entregó {int(e["recibido"])} de {total}' if e else "Pendiente"
        salida.append({"nombre": m["nombre"], "dosis_mg": m["dosis_mg"], "falta": falta,
                       "total": total, "motivo": motivo})
    return salida


def dias_restantes(s, med, fecha):
    por_dia = tomas_por_dia(med)
    return inventario(s, med, fecha) // por_dia if por_dia else 0


def aviso_compras(s):
    """Compras próximas (medicinas que alcanzan para pocos días)."""
    v = visita_actual(s)
    if not v:
        return []
    salida = []
    for m in v["meds"]:
        inv = inventario(s, m, v["fecha"])
        if inv <= 0:
            continue
        dias = dias_restantes(s, m, v["fecha"])
        if dias < int(m["dias"]):
            limite = date.today() + timedelta(days=max(dias - 1, 0))
            salida.append({"nombre": m["nombre"], "dias": dias, "limite": limite.isoformat()})
    return salida


# ---------- dosis del día ----------
def dosis_hoy(s):
    v = visita_actual(s)
    if not v:
        return []
    tomadas = set(s["tomas"].get(hoy_iso(), []))
    salida = []
    for m in v["meds"]:
        sin_medicina = inventario(s, m, v["fecha"]) <= 0 and not falta_respuesta_iess(s)
        for h in horarios_de(m):
            did = f'{m["nombre"]}@{h}'
            salida.append({"id": did, "nombre": m["nombre"], "dosis_mg": m["dosis_mg"], "hora": h,
                           "tomada": did in tomadas, "sin_medicina": sin_medicina and did not in tomadas})
    return sorted(salida, key=lambda d: d["hora"])


def resumen_dia(s):
    dosis = dosis_hoy(s)
    tomadas = sum(1 for d in dosis if d["tomada"])
    pendientes = [d for d in dosis if not d["tomada"] and not d["sin_medicina"]]
    return {"dosis": dosis, "tomadas": tomadas, "total": len(dosis),
            "pct": int(100 * tomadas / len(dosis)) if dosis else 0,
            "siguiente": pendientes[0] if pendientes else None,
            "sin_medicina": [d for d in dosis if d["sin_medicina"]]}


# ---------- avisos ----------
def generar_avisos(s):
    """Avisos que ya corresponden por hora y que aún no se mostraron. Modifica s['enviados']."""
    avisos = list(s.get("cola", []))
    s["cola"] = []
    hora = ahora(s)
    for d in dosis_hoy(s):
        if d["tomada"] or d["hora"] > hora:
            continue
        if d["sin_medicina"]:
            clave = f'{hoy_iso()}|{d["id"]}|compra'
            if clave not in s["enviados"]:
                s["enviados"].append(clave)
                avisos.append({"tipo": "compra", "titulo": "Falta una medicina",
                               "cuerpo": f'No tienes {d["nombre"]} para la toma de las {d["hora"]}. Mira dónde comprarla.',
                               "corto": "Tienes una medicina pendiente por comprar.", "url": "/farmacias"})
        else:
            clave = f'{hoy_iso()}|{d["id"]}|toma'
            if clave not in s["enviados"]:
                s["enviados"].append(clave)
                avisos.append({"tipo": "toma", "titulo": "Es hora de tu medicina",
                               "cuerpo": f'{d["hora"]} · {d["nombre"]} {d["dosis_mg"]} mg',
                               "corto": f'Es hora de tu medicina de las {d["hora"]}.', "dosis": d["id"], "url": "/plan"})
    return avisos


def aviso_manual(tipo, s):
    if tipo == "compra":
        f = faltantes(s)
        if f:
            nombres = ", ".join(x["nombre"] for x in f)
            return {"tipo": "compra", "titulo": "Falta comprar medicinas", "cuerpo": f"Te falta: {nombres}.",
                    "corto": "Tienes medicinas pendientes por comprar.", "url": "/farmacias"}
        return {"tipo": "compra", "titulo": "Recompra próxima", "cuerpo": "Tu Metformina alcanza para pocos días.",
                "corto": "Pronto tendrás que comprar medicina.", "url": "/farmacias"}
    if tipo == "cita":
        c = s["perfil"].get("cita", "")
        return {"tipo": "cita", "titulo": "Control médico mañana",
                "cuerpo": f'Cita: {fecha_corta(c)} a las {c[11:16]}' if c else "Tienes una cita médica.",
                "corto": "Mañana tienes un control médico.", "url": "/plan"}
    return None


# ---------- farmacias ----------
def km(lat1, lng1, lat2, lng2):
    p1, p2 = radians(lat1), radians(lat2)
    a = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lng2 - lng1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


def stock_de(s, farmacia, nombre):
    """Stock simulado menos lo que ya se vendió en esta demo."""
    base = farmacia["stock"].get(nombre, 0)
    return max(0, base - int(s.get("vendido", {}).get(str(farmacia["id"]), {}).get(nombre, 0)))


def farmacias_cercanas(s, lista_faltantes, lat, lng, maximo=4):
    """Primero las que tienen todo lo que falta (de la más cercana a la más lejana); luego el resto."""
    salida = []
    for f in FARMACIAS:
        dist = km(lat, lng, f["lat"], f["lng"])
        stock = []
        cubre = 0
        for x in lista_faltantes:
            u = stock_de(s, f, x["nombre"])
            estado = "hay" if u >= x["falta"] else ("poco" if u > 0 else "no")
            cubre += estado == "hay"
            stock.append({"nombre": x["nombre"], "dosis_mg": x["dosis_mg"], "unidades": u, "estado": estado})
        salida.append({**f, "dist": dist, "stock": stock, "cubre": cubre,
                       "completa": cubre == len(lista_faltantes)})
    salida.sort(key=lambda f: (not f["completa"], f["dist"]))
    return salida[:maximo]


def mapa(lat, lng, farmacias, ancho=350, alto=170, margen=28):
    """Posiciones (x, y) en un SVG sin mapa de fondo: no depende de internet."""
    puntos = [(lat, lng)] + [(f["lat"], f["lng"]) for f in farmacias]
    k = cos(radians(lat))
    xs = [p[1] * k for p in puntos]
    ys = [-p[0] for p in puntos]
    rx = max(max(xs) - min(xs), 1e-4)
    ry = max(max(ys) - min(ys), 1e-4)
    esc = min((ancho - 2 * margen) / rx, (alto - 2 * margen) / ry)
    ox = (ancho - rx * esc) / 2 - min(xs) * esc
    oy = (alto - ry * esc) / 2 - min(ys) * esc
    return [(round(x * esc + ox, 1), round(y * esc + oy, 1)) for x, y in zip(xs, ys)]


# ---------- pedido recurrente ----------
def pedido_mensual(s, lat, lng):
    """Lo que se necesita para un mes con la receta actual y la mejor farmacia para pedirlo."""
    v = visita_actual(s)
    if not v or falta_respuesta_iess(s):
        return None
    items = [{"nombre": m["nombre"], "dosis_mg": m["dosis_mg"], "unidades": total_recetado(m)} for m in v["meds"]]
    mejor = None
    for f in FARMACIAS:
        completo = all(stock_de(s, f, i["nombre"]) >= i["unidades"] for i in items)
        clave = (not completo, km(lat, lng, f["lat"], f["lng"]))
        if mejor is None or clave < mejor[0]:
            mejor = (clave, f, completo)
    if mejor is None:
        return None
    f = mejor[1]
    return {"items": items, "farmacia": f, "dist": km(lat, lng, f["lat"], f["lng"]), "completo": mejor[2]}


# ---------- resumen para el médico ----------
def resumen_medico(s):
    """Lo que el paciente debe contarle al médico en el control, con datos de la receta y del IESS."""
    v = visita_actual(s)
    if not v:
        return None
    previa = visita_previa(s, v["fecha"])
    filas = comparar(v, previa)
    frases = []
    for m in filas:
        if m["estado"] == "aumentada":
            frases.append(f'Me aumentaron la {m["nombre"]}: {m["detalle"]}.')
        elif m["estado"] == "reducida":
            frases.append(f'Me redujeron la {m["nombre"]}: {m["detalle"]}.')
        elif m["estado"] == "frecuencia":
            frases.append(f'Cambió la frecuencia de {m["nombre"]}: ahora cada {m["cada_horas"]} h.')
        elif m["estado"] == "nuevo":
            frases.append(f'Me agregaron {m["nombre"]} {m["dosis_mg"]} mg.')
        elif m["estado"] == "suspendido":
            frases.append(f'Ya no tengo recetada la {m["nombre"]}.')
    entregas = []
    if s["perfil"].get("iess"):
        for m in v["meds"]:
            e = entrega_de(s, v["fecha"], m["nombre"])
            total = total_recetado(m)
            if not e:
                continue
            if e["estado"] == "no":
                frases.append(f'El IESS no me entregó {m["nombre"]}.')
            elif e["estado"] == "parcial":
                frases.append(f'El IESS solo me entregó {int(e["recibido"])} de {total} de {m["nombre"]}.')
            entregas.append({"nombre": m["nombre"], "estado": e["estado"], "recibido": int(e["recibido"]), "total": total})
    return {"visita": v, "filas": filas, "frases": frases, "entregas": entregas,
            "falta": faltantes(s), "previa": previa}
