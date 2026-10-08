-- Catálogos. Farmacias REALES del grupo Farmaenlace cerca de Puembo (sede del hackatón),
-- tomadas de Google Maps el 2026-10-08 (ver db/farmacias.sql y tratamiento-app/data.py).
-- El STOCK es simulado.

INSERT INTO cadena (id, nombre) VALUES
    (1, 'Económicas'),
    (2, 'Medicity');

INSERT INTO medicamento (id, nombre_generico, presentacion) VALUES
    (1, 'Losartán',      'Tableta'),
    (2, 'Metformina',    'Tableta'),
    (3, 'Atorvastatina', 'Tableta'),
    (4, 'Amlodipino',    'Tableta'),
    -- extra, para dar variedad a los pacientes fake
    (5, 'Enalapril',     'Tableta'),
    (6, 'Glibenclamida', 'Tableta'),
    (7, 'Levotiroxina',  'Tableta'),
    (8, 'Omeprazol',     'Cápsula');

INSERT INTO condicion (id, nombre) VALUES
    (1, 'Hipertensión'),
    (2, 'Diabetes tipo 2'),
    (3, 'Dislipidemia'),
    (4, 'Hipotiroidismo'),
    (5, 'Gastritis crónica');

INSERT INTO farmacia (id, cadena_id, sucursal, parroquia, direccion, lat, lng, hora_cierre, horario_detalle) VALUES
    (1,  2, 'Puembo',            'Puembo',           'Manuel Burbano',                        -0.1774634, -78.3588022, '20:30', 'Lun-vie 8:00-20:30; sáb y dom 9:00-19:00'),
    (2,  1, 'Puembo Centro',     'Puembo',           'Simón Bolívar y 24 de Mayo',            -0.1786097, -78.3589010, '20:00', NULL),
    (3,  1, 'Puembo',            'Puembo',           '24 de Mayo y Humberto Duque',           -0.1984982, -78.3680239, '20:00', 'Lun-vie 8:00-20:00; sáb y dom 10:00-19:00'),
    (4,  2, 'Puembo 24 de Mayo', 'Puembo',           '24 de Mayo y Patricio Romero',          -0.1998237, -78.3676522, '21:30', 'Lun-vie 7:00-21:30; sáb y dom 8:00-21:00'),
    (5,  1, 'Yaruquí',           'Yaruquí',          'Av. Amazonas',                          -0.1624381, -78.3200072, '21:00', 'Lun-sáb 7:00-21:00; dom 8:00-20:00'),
    (6,  2, 'Vía Pifo',          'Puembo / Tumbaco', 'Av. Guayasamín y Ruta Viva',            -0.2105018, -78.3643521, '21:00', 'Lun-vie 8:00-21:00; sáb y dom 8:00-20:00'),
    (7,  1, 'Tumbaco Villavega', 'Tumbaco',          'Villa Vega y Av. Guayasamín',           -0.2097980, -78.3868623, '21:00', 'Lun-sáb 8:00-21:00; dom 8:00-20:00'),
    (8,  1, 'Pifo Chaupimolino', 'Pifo',             'Chaupimolino',                          -0.2196237, -78.3388996, '21:00', 'Lun-vie 7:00-21:00; sáb y dom 8:00-20:00'),
    (9,  2, 'Tumbaco Central',   'Tumbaco',          'Juan Montalvo y Fray Gonzalo de Vera',  -0.2135730, -78.4056652, '21:00', 'Lun-vie 7:30-21:00; sáb 7:30-20:30; dom 7:30-19:30'),
    (10, 2, 'Tumbaco La Cerámica', 'Tumbaco',        'La Cerámica',                           -0.2211377, -78.3929391, '21:00', 'Lun-vie 8:00-21:00; sáb y dom 9:00-20:00'),
    (11, 1, 'Pifo Gonzalo Pizarro', 'Pifo',          'Gonzalo Pizarro',                       -0.2242182, -78.3407142, '21:00', 'Lun-vie 6:30-21:00; sáb 7:30-21:00; dom 7:30-20:00');

-- @stock
-- Stock simulado. Columnas = Losartán, Metformina, Atorvastatina, Amlodipino (igual que data.py)
--                           + Enalapril, Glibenclamida, Levotiroxina, Omeprazol (nuevos).
-- "Restablecer datos" del panel Demo vuelve a ejecutar este bloque (ON CONFLICT).
INSERT INTO farmacia_stock (farmacia_id, medicamento_id, unidades)
SELECT s.f, x.medicamento_id, x.unidades
FROM (VALUES
    (1,  ARRAY[80, 100, 60, 25,   40, 30, 20, 50]),
    (2,  ARRAY[30,  55,  0, 18,   20,  0, 15, 35]),
    (3,  ARRAY[ 0,  22, 30,  0,   10, 25,  0, 20]),
    (4,  ARRAY[45,   8, 20, 40,   30, 12, 10,  0]),
    (5,  ARRAY[20,  36,  6, 12,    0, 18, 25, 40]),
    (6,  ARRAY[12,   0,  0,  9,   15,  0,  5, 10]),
    (7,  ARRAY[70,  64, 48, 33,   50, 40, 30, 60]),
    (8,  ARRAY[18,  14, 10,  7,    8,  6,  0, 12]),
    (9,  ARRAY[26,  31,  0, 15,   22, 14, 18,  0]),
    (10, ARRAY[50,  50, 25, 20,   35, 20, 12, 30]),
    (11, ARRAY[35,  25, 15, 10,   25, 15, 10, 20])
) AS s (f, stock)
CROSS JOIN LATERAL unnest(s.stock) WITH ORDINALITY AS x (unidades, medicamento_id)
ON CONFLICT (farmacia_id, medicamento_id) DO UPDATE SET unidades = EXCLUDED.unidades;
-- @fin

-- "vence" en data.py es texto relativo ("Hoy", "Hasta el domingo"): aquí, fechas relativas a hoy
INSERT INTO promocion (titulo, detalle, medicamento_id, vigente_hasta) VALUES
    ('15% de descuento en Metformina',
     'Tratamientos de 30 días o más. Con tarjeta de fidelidad.', 2, CURRENT_DATE),
    ('2x1 en tiras reactivas de glucosa',
     'Para controlar la diabetes en casa.', NULL,
     CURRENT_DATE + (7 - EXTRACT(ISODOW FROM CURRENT_DATE))::INT),
    ('10% en tensiómetros digitales',
     'Para medir la presión en casa.', 1,
     CURRENT_DATE + (7 - EXTRACT(ISODOW FROM CURRENT_DATE))::INT),
    ('Envío gratis desde $15',
     'En pedidos de medicinas de tratamiento crónico.', NULL, CURRENT_DATE);
