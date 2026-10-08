# Mi tratamiento · demo del hackatón

App web (Flask + HTML/JS) para que a nadie se le acabe la medicina a mitad del tratamiento.
Todo el stock, las farmacias y el paciente son **datos de ejemplo**.

## Correrla en VSCode

1. Abre la carpeta `tratamiento-app` en VSCode (Archivo → Abrir carpeta).
2. Abre la terminal de VSCode (Ctrl + ñ) y ejecuta:

   **Windows (PowerShell)**
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```
   **Mac / Linux**
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python3 app.py
   ```
3. Abre http://localhost:5000 en Chrome.
4. Para verla como celular: F12 → Ctrl + Shift + M (modo dispositivo), o achica la ventana.

Si el puerto 5000 está ocupado: `$env:PORT=5001; python app.py` (PowerShell), `set PORT=5001` (cmd) o `PORT=5001 python3 app.py` (Mac/Linux).

## Login y base de datos

La app pide **login**: cada usuario ve solo los datos de su paciente. Hay dos modos:

| Modo | Cuándo | Usuarios |
|---|---|---|
| **JSON** (por defecto) | Sin `DATABASE_URL`. Todo vive en `data/state.json`, como antes | Solo `luis.mora@demo.ec` / `demo1234` |
| **PostgreSQL** | Con `DATABASE_URL`. Es como corre en AWS | 11 pacientes de prueba, todos con contraseña `demo1234` (la lista aparece en el login) |

Para usar PostgreSQL en local (necesita Docker Desktop), desde la raíz del repo:

```powershell
docker compose -f db/docker-compose.yml up -d
$env:DATABASE_URL = "postgresql://goble:goble@localhost:5432/tratamiento"
python app.py
```

**Restablecer datos de ejemplo** (panel Demo) vuelve solo al paciente con el que entraste a su estado inicial.

Pruebas automáticas (desde esta carpeta): `python -m pytest tests -v`. Con `DATABASE_URL` también prueban el login, el aislamiento entre usuarios y cada escritura en la base.

## Lectura de recetas con IA

`ai.py` usa Claude si encuentra credenciales; si no, devuelve una receta de ejemplo:

- **En AWS:** Claude en Amazon Bedrock (`AI_PROVIDER=bedrock`), con el rol IAM de la Lambda. El modelo se elige con `CLAUDE_MODEL` (por defecto `anthropic.claude-opus-5-5`).
- **En local:** `$env:ANTHROPIC_API_KEY = "..."` para usar la API de Anthropic directamente.

## Guion de la demo (2 minutos)

1. **Hoy:** "2 de 4 dosis tomadas" y la alerta roja: falta comprar 2 medicamentos.
2. **Receta:** la IA lee la foto y marca "Dosis aumentada" y "Medicamento nuevo" frente a la visita anterior.
3. **Entrega del IESS:** completo / parcial / sin stock, por cada medicamento.
4. Botón **Demo → Simular que son las 20:00:** aparece el aviso emergente. Tocar "Ya la tomé".
5. **Farmacias:** la más cercana con todo lo que falta. "Pedir envío".
6. **Hoy** vuelve en verde: "Todo al día".

El botón **Demo** (arriba a la derecha) simula la hora, dispara avisos y **restablece los datos de ejemplo** para repetir la demo.

## Quién toca qué

| Archivo | Para qué sirve | Quién |
|---|---|---|
| `ai.py` | Leer la receta desde la foto con IA (Bedrock o API de Anthropic; sin credenciales, receta de ejemplo) | Edu |
| `data.py` | Farmacias, stock simulado y guardado del estado (JSON o PostgreSQL) | Edu |
| `db.py` | Lectura y escritura en PostgreSQL (`db/init/` en la raíz tiene el esquema) | Edu |
| `dbinit.py`, `lambda_handler.py` | Entradas de AWS Lambda: cargar la base y servir Flask | Edu |
| `logic.py` | Reglas: comparar recetas, faltantes, avisos, farmacia cercana | Los dos |
| `app.py` | Rutas de Flask | Edu |
| `templates/*.html` y `static/css/app.css` | Pantallas y estilos | Faty |
| `static/js/app.js` | Avisos, ubicación y panel Demo | Los dos |

Cambiar el color o el texto de una pantalla: edita su archivo en `templates/` y recarga el navegador.

## Probarla en tu celular Android (ngrok)

1. Instala ngrok y crea una cuenta gratis: https://ngrok.com
2. Con la app corriendo: `ngrok http 5000`
3. Abre en Chrome del celular la dirección `https://…ngrok…` que muestra ngrok.
4. Menú de Chrome → **Instalar aplicación** (o "Añadir a pantalla de inicio").
5. En la pantalla Hoy toca **Activar notificaciones** y acepta el permiso.

La dirección de ngrok cambia cada vez que lo reinicias.

## Qué hacen hoy los avisos (y qué no)

- **Sí:** aviso emergente dentro de la app y, si activas las notificaciones, aviso del sistema cuando la app no está a la vista. Se consultan cada 4 segundos.
- **Todavía no:** avisar con la app **cerrada**. Para eso falta Web Push desde el servidor (siguiente paso). Si el celular suspende la página, el aviso del sistema puede no llegar.

## Supuestos de la demo (decirlo en el pitch)

- 1 tableta por toma. Los días restantes se estiman con lo recibido o comprado para la receta actual.
- El stock y las farmacias son simulados. La lectura de la receta es simulada hasta conectar `ai.py`.
- La app solo registra lo que dice la receta: nunca sugiere ni cambia dosis.
- El paciente (o su cuidador) debe dar su consentimiento para guardar datos de salud.
