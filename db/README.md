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

Los scripts de `init/` corren en orden **solo la primera vez**, cuando el volumen está vacío. En AWS los ejecuta la Lambda `db-init` (ver [infra/README.md](../infra/README.md)). Para resetear la data local:

```bash
docker compose -f db/docker-compose.yml down -v
docker compose -f db/docker-compose.yml up -d
```

## Archivos

| Archivo | Contenido |
|---|---|
| `init/001_schema.sql` | Enums, tablas, restricciones y vistas |
| `init/002_catalogos.sql` | 2 cadenas, las 11 farmacias reales de Farmaenlace cerca de Puembo (de `farmacias.sql`), 8 medicamentos, stock simulado, promociones y condiciones |
| `init/003_paciente_demo.sql` | Luis Mora (id 1), espejo exacto de `data.py::seed()` |
| `init/004_pacientes_fake.sql` | **Generado.** 10 pacientes (ids 2-11), uno por caso |
| `init/005_usuarios.sql` | **Generado.** Un usuario de login por paciente (contraseña `demo1234`) |
| `init/999_sync_sequences.sql` | Alinea las secuencias tras insertar IDs fijos |
| `gen_pacientes_fake.py` | Regenera `004` y `005` (determinista): `py db/gen_pacientes_fake.py` |
| `farmacias.sql` | Fuente original de las farmacias (Google Maps). Su contenido ya está en `002` |

Los bloques `-- @paciente N` y `-- @stock` marcan qué partes de las semillas vuelve a ejecutar
el botón **Restablecer datos** del panel Demo: borra al paciente de la sesión, lo vuelve a cargar
desde su bloque y repone el stock de las farmacias.

## Modelo

```
cadena ─< farmacia ─< farmacia_stock >─ medicamento ─< promocion
                │                            │
usuario ── paciente ─< visita ─< receta_item >──────────┘
   │  │               │  ├── entrega_iess (1:1)
   │  │               │  ├─< compra_item >─ compra >─ farmacia
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
| `compra` + `compra_item` | `compras`. Comprar descuenta `farmacia_stock`, así que `vendido` desaparece |
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

## Consultas útiles

```sql
SELECT * FROM v_paciente ORDER BY id;
SELECT * FROM v_faltantes WHERE paciente_id = 1;
SELECT nombre, horarios, total FROM v_receta_item_total WHERE paciente_id = 11;
SELECT extraccion_ia -> 'medicamentos' FROM visita WHERE origen = 'ia';

-- Farmacias con stock de lo que le falta al paciente 1
SELECT c.nombre || ' · ' || f.sucursal AS farmacia, m.nombre_generico, s.unidades, ft.falta
FROM v_faltantes ft
JOIN medicamento m    ON m.nombre_generico = ft.nombre
JOIN farmacia_stock s ON s.medicamento_id = m.id
JOIN farmacia f       ON f.id = s.farmacia_id
JOIN cadena c         ON c.id = f.cadena_id
WHERE ft.paciente_id = 1 AND s.unidades > 0
ORDER BY farmacia;
```
