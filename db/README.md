# Base de datos: PostgreSQL 17

Modelo relacional de `apps/frontend/tratamiento-app`, con data fake de pacientes.
Es **híbrido**: relacional para todo lo que se cruza (recetas, entregas del IESS, compras, stock). Los datos con forma de documento usan tipos nativos de Postgres:

- `receta_item.horarios TIME[]`: los horarios se leen siempre junto con su medicamento.
- `visita.extraccion_ia JSONB`: salida cruda de `ai.py`, guardada para auditoría. Es `NULL` en recetas manuales.

## Levantar

Requiere Docker Desktop corriendo.

```bash
docker compose -f db/docker-compose.yml up -d
```

- **Conexión:** `postgresql://goble:goble@localhost:5432/tratamiento`. Si el puerto está ocupado, usa `PG_PORT=5433 docker compose ...`.
- **Zona horaria:** `America/Guayaquil`, para que `CURRENT_DATE` y las horas de las tomas cuadren con la app.
- **Consola SQL:** `docker exec -it goble-postgres psql -U goble -d tratamiento`

Los scripts de `init/` corren en orden **solo la primera vez**, cuando el volumen está vacío. Los datos de Farmaenlace (`datos_farmaenlace/`) los carga `init/001b_datos_farmaenlace.sh` justo después del esquema. En AWS los ejecuta la Lambda `db-init` (ver [infra/README.md](../infra/README.md)). Para resetear la data local:

```bash
docker compose -f db/docker-compose.yml down -v
docker compose -f db/docker-compose.yml up -d
```

## Archivos

| Archivo | Contenido |
|---|---|
| `init/001_schema.sql` | Enums, tablas (incluye `farmacias`, `medicinas` y `stock`), restricciones y vistas |
| `init/001b_datos_farmaenlace.sh` | Solo docker compose: carga `datos_farmaenlace/*.sql` en orden (la Lambda lo ignora y lo hace `db.py`) |
| `init/002_catalogos.sql` | Condiciones y promociones (simuladas) |
| `init/003_paciente_demo.sql` | Luis Mora (id 1), espejo exacto de `data.py::seed()` |
| `init/004_pacientes_fake.sql` | **Generado.** 10 pacientes (ids 2-11), uno por caso |
| `init/005_usuarios.sql` | **Generado.** Un usuario de login por paciente (contraseña `demo1234`) |
| `init/006_abastecimiento.sql` | Módulo de abastecimiento: reloj de la demo, cuidadores, productos relacionados, medicamentos controlados y la vista `v_saldo_medicacion` |
| `init/007_pacientes_cuidadores.sql` | **Generado.** 4 pacientes con movilidad reducida (ids 12-15), 3 cuidadores y sus logins |
| `init/008_eventos.sql` | Alertas idempotentes (`alerta`) y registro de eventos (`evento_log`) del evaluador |
| `init/999_sync_sequences.sql` | Alinea las secuencias tras insertar IDs fijos |
| `gen_pacientes_fake.py` | Regenera `004` y `005` (determinista): `py db/gen_pacientes_fake.py` |
| `datos_farmaenlace/farmacias.sql` | 11 farmacias reales de Farmaenlace (Económicas y Medicity) cerca de Puembo, de Google Maps (2026-10-08) |
| `datos_farmaenlace/medicinas.sql` | 187 medicinas en 16 grupos (incluye insulina, levodopa, anticoagulantes). `uid` FE-xxxxx **provisional**; efectos secundarios y laboratorio por validar |
| `datos_farmaenlace/stock.sql` | Stock **simulado**: 11 farmacias × 187 medicinas = 2.057 filas (`uid` FE-STK-xxxxxx). Contiene el bloque `@stock` |

Los bloques `-- @paciente N` y `-- @stock` marcan qué partes de las semillas vuelve a ejecutar
el botón **Restablecer datos** del panel Demo: borra al paciente de la sesión, lo vuelve a cargar
desde su bloque y repone el stock de las farmacias.

## Modelo

```
farmacias ─< stock >─ medicinas ─< promocion
    │                        │
usuario ── paciente ─< visita ─< receta_item >┘
   │  │               │  ├── entrega_iess (1:1)
   │  │               │  ├─< compra_item >─ compra >─ farmacias
   │  │               │  └─< toma
   │  ├─< cita        │
   │  └─< aviso       │
   └─< paciente_condicion >─ condicion
```

| Tabla | Equivale en `data/state.json` |
|---|---|
| `usuario` | Login de la demo: cada usuario ve solo su paciente (contraseña con hash de werkzeug) |
| `paciente`, `paciente_condicion`, `cita` | `perfil`. La edad se calcula a partir de `fecha_nacimiento` |
| `visita` + `receta_item` | `visitas[].meds[]` |
| `entrega_iess` | `entregas[fecha][med]`. Sin filas = el IESS aún no responde |
| `compra` + `compra_item` | `compras`. Comprar descuenta `stock`, así que `vendido` desaparece |
| `toma` | `tomas[fecha]` (`"Losartán@08:00"`) |
| `aviso` | `enviados` + `cola`. `mostrado_en IS NULL` = en cola |

`sim_hora`, la hora simulada del panel Demo, no se guarda en la base.

### Vistas: replican `logic.py`

| Vista | Función de `logic.py` |
|---|---|
| `v_visita_actual` | `visita_actual()` |
| `v_receta_item_total` | `tomas_por_dia()`, `total_recetado()` |
| `v_inventario` | `recibido_iess()` + `comprado()`, `dias_restantes()` |
| `v_falta_respuesta_iess` | `falta_respuesta_iess()` |
| `v_faltantes` | `faltantes()`, con el mismo texto de `motivo` |
| `v_paciente` | perfil con `edad`, `condiciones[]` y `proxima_cita` |

## Pacientes fake

Todos usan la contraseña `demo1234`. El correo sale del nombre: `luis.mora@demo.ec`, `carmen.pazmino@demo.ec`, etc. (la lista completa aparece en la pantalla de login).

| id | Caso | Qué se ve |
|---|---|---|
| 1 | **Demo** (Luis Mora) | Faltan Metformina (32) y Atorvastatina (30) |
| 2 | Sin IESS | Le falta todo: Enalapril 60, Atorvastatina 30 |
| 3 | IESS entregó todo | Sin faltantes |
| 4 | IESS aún no responde | Aparece en `v_falta_respuesta_iess` |
| 5 | Primera visita | Falta Atorvastatina |
| 6 | Medicamento suspendido | Amlodipino estaba en la visita anterior y ya no |
| 7 | Dosis reducida | Metformina 1000 → 500 mg; el IESS entregó 40 de 60 |
| 8 | Cambio de frecuencia | Metformina cada 24 h → cada 12 h |
| 9 | Compró lo que faltaba | IESS parcial + `compra`: sin faltantes |
| 10 | Sin consentimiento | Perfil incompleto, sin cuidador ni condiciones |
| 11 | Caso cargado, receta leída con IA | 5 medicamentos, `extraccion_ia` con nombres crudos, aviso en cola |
| 12 | **Parkinson** (Jorge Quishpe) | Levodopa **por agotarse** (6 días); cuidadora Ana Quishpe |
| 13 | **Alzheimer** (Rosa Quishpe) | Memantina **agotada** (el IESS entregó 20 de 60); misma cuidadora Ana |
| 14 | **Cuadriplejia** (Patricio Andrade) | Todo **ok** (25 días); con "Simular +20 días" pasa a por agotarse. Dos cuidadores |
| 15 | **Cuidados paliativos** (Mercedes Yánez) | **IESS sin responder**; tramadol marcado como controlado |

## Módulo de abastecimiento: saldo real

`v_saldo_medicacion` calcula, por medicamento de la receta vigente, cuánto le queda al paciente.
`apps/frontend/tratamiento-app/abastecimiento/calculo.py` aplica las mismas reglas, y las pruebas verifican que coincidan.

```
unidades_obtenidas = entregado por el IESS + comprado
fecha_agotamiento  = inicio de la receta + unidades_obtenidas / tomas por día
dias_restantes     = fecha_agotamiento - fecha_referencia()        (mínimo 0)
estado             = sin_respuesta_iess | agotado | por_agotarse (≤ paciente.umbral_dias) | ok
```

Supuestos: 1 tableta por toma y adherencia completa desde la fecha de la receta.

**Reloj de la demo:** `fecha_referencia()` devuelve la fecha guardada en `config_demo`, o la fecha real si no hay ninguna. Así la UI, la API y el evaluador ven el mismo "hoy" cuando se simulan días:

```sql
INSERT INTO config_demo VALUES ('fecha_referencia', (CURRENT_DATE + 20)::text)
  ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor;   -- simular +20 días
DELETE FROM config_demo WHERE clave = 'fecha_referencia';     -- volver a hoy
```

| Tabla nueva | Contenido |
|---|---|
| `cuidador`, `paciente_cuidador` | Un cuidador con varios pacientes (rol `principal` / `apoyo`) |
| `producto`, `regla_sugerencia` | Productos no medicamentosos sugeridos por condición o por grupo de medicina |
| `config_demo` | Reloj de la demo |
| Columnas nuevas | `paciente.umbral_dias`, `direccion_entrega`, `movilidad_reducida`; `medicinas.controlado` (provisional, validar con ARCSA) |

### Evaluador y eventos

`apps/frontend/tratamiento-app/abastecimiento/evaluador.py` revisa `v_saldo_medicacion` y, por cada paciente con alertas **nuevas**, publica:

| Evento | Cuándo | Contenido |
|---|---|---|
| `MedicacionPorAgotarse` | Un medicamento está por agotarse (≤ `umbral_dias`) o agotado | Cuidadores, farmacias sugeridas, productos relacionados, `solo_retiro` si es controlado |
| `EntregaIessIncompleta` | El IESS entregó parcial o nada (y aún falta), o no respondió | Recibido, comprado, total y falta por medicamento |
| `DemandaPrevista` | Hay algo que comprar | Para la mejor farmacia: medicina, cantidad y fecha. **Sin datos del paciente** |

- **Sin duplicados:** la tabla `alerta` evita repetir un aviso en el mismo día de referencia. El aviso de entrega incompleta sale una sola vez por receta.
- **Reevaluación inmediata:** guardar una receta, una entrega del IESS o una compra publica `PacienteActualizado`, que reevalúa a ese paciente al instante.
- **Sin AWS:** si no hay `EVENT_BUS_NAME`, los eventos se despachan en proceso siguiendo la misma tabla de rutas que tendrán las reglas de EventBridge (`abastecimiento/eventos.py`). Todo queda en `evento_log`.

Para probarlo en local (desde `apps/frontend/tratamiento-app`, con `DATABASE_URL`):

```powershell
python -m handlers.evaluador                # evalúa a todos con el reloj actual
python -m handlers.evaluador --avanzar 20   # simula +20 días y evalúa
python -m handlers.evaluador --hoy          # vuelve el reloj a la fecha real
```

## Consultas útiles

```sql
SELECT * FROM v_paciente ORDER BY id;
SELECT * FROM v_faltantes WHERE paciente_id = 1;
SELECT nombre, horarios, total FROM v_receta_item_total WHERE paciente_id = 11;
SELECT extraccion_ia -> 'medicamentos' FROM visita WHERE origen = 'ia';

-- Farmacias con stock de lo que le falta al paciente 1
SELECT f.nombre AS farmacia, m.nombre, m.concentracion, s.cantidad, ft.falta
FROM v_faltantes ft
JOIN receta_item ri ON ri.id = ft.receta_item_id
JOIN medicinas m    ON m.uid = ri.uid_medicina
JOIN stock s        ON s.uid_medicina = m.uid
JOIN farmacias f    ON f.uid = s.uid_farmacia
WHERE ft.paciente_id = 1 AND s.cantidad > 0
ORDER BY farmacia;
```
