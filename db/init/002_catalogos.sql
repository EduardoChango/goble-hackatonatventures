-- Catálogos de la app: condiciones y promociones (simuladas).
-- Farmacias, medicinas y stock (data Farmaenlace) viven en db/datos_farmaenlace/ y se cargan ANTES de este archivo.

INSERT INTO condicion (id, nombre) VALUES
    (1, 'Hipertensión'),
    (2, 'Diabetes tipo 2'),
    (3, 'Dislipidemia'),
    (4, 'Hipotiroidismo'),
    (5, 'Gastritis crónica');

-- "vence" en data.py es texto relativo ("Hoy", "Hasta el domingo"): aquí, fechas relativas a hoy
INSERT INTO promocion (titulo, detalle, uid_medicina, vigente_hasta) VALUES
    ('15% de descuento en Metformina',
     'Tratamientos de 30 días o más. Con tarjeta de fidelidad.', 'FE-00051', CURRENT_DATE),
    ('2x1 en tiras reactivas de glucosa',
     'Para controlar la diabetes en casa.', NULL,
     CURRENT_DATE + (7 - EXTRACT(ISODOW FROM CURRENT_DATE))::INT),
    ('10% en tensiómetros digitales',
     'Para medir la presión en casa.', 'FE-00001',
     CURRENT_DATE + (7 - EXTRACT(ISODOW FROM CURRENT_DATE))::INT),
    ('Envío gratis desde $15',
     'En pedidos de medicinas de tratamiento crónico.', NULL, CURRENT_DATE);
