-- Catálogos. Farmacias, stock y promociones copiados de tratamiento-app/data.py.
-- Coordenadas aproximadas de Ambato; cantidades inventadas.

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

INSERT INTO farmacia (id, cadena_id, sucursal, lat, lng, hora_cierre) VALUES
    (1,  1, 'Centro',            -1.2519, -78.6167, '21:00'),
    (2,  2, 'Centro Comercial',  -1.2441, -78.6102, '22:00'),
    (3,  1, 'Ficoa',             -1.2334, -78.6230, '20:00'),
    (4,  1, 'Terminal',          -1.2572, -78.6089, '21:00'),
    (5,  2, 'Huachi',            -1.2685, -78.6270, '21:30'),
    (6,  1, 'Atocha',            -1.2296, -78.6341, '20:00'),
    (7,  1, 'Pishilata',         -1.2630, -78.5990, '21:00'),
    (8,  2, 'Ingahurco',         -1.2380, -78.6130, '22:00'),
    (9,  1, 'Miraflores',        -1.2450, -78.6240, '20:30'),
    (10, 1, 'Izamba',            -1.2040, -78.5780, '20:00');

-- Stock: columnas = Losartán, Metformina, Atorvastatina, Amlodipino (data.py)
--        + Enalapril, Glibenclamida, Levotiroxina, Omeprazol (nuevos)
INSERT INTO farmacia_stock (farmacia_id, medicamento_id, unidades)
SELECT s.f, x.medicamento_id, x.unidades
FROM (VALUES
    (1,  ARRAY[60, 40, 30, 25,   40, 30, 20, 50]),
    (2,  ARRAY[30, 22,  0, 18,   20,  0, 15, 35]),
    (3,  ARRAY[ 0, 55, 30,  0,   10, 25,  0, 20]),
    (4,  ARRAY[45,  8, 20, 40,   30, 12, 10,  0]),
    (5,  ARRAY[20, 36,  6, 12,    0, 18, 25, 40]),
    (6,  ARRAY[12,  0,  0,  9,   15,  0,  5, 10]),
    (7,  ARRAY[70, 64, 48, 33,   50, 40, 30, 60]),
    (8,  ARRAY[18, 14, 10,  7,    8,  6,  0, 12]),
    (9,  ARRAY[26, 31,  0, 15,   22, 14, 18,  0]),
    (10, ARRAY[50, 50, 25, 20,   35, 20, 12, 30])
) AS s (f, stock)
CROSS JOIN LATERAL unnest(s.stock) WITH ORDINALITY AS x (unidades, medicamento_id);

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
