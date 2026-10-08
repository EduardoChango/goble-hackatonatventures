-- Farmacias del grupo Farmaenlace (Farmacias Económicas y Medicity) cerca de Puembo, Quito.
-- Datos tomados de Google Maps el 2026-10-08: pueden cambiar. El stock NO está aquí.
-- Uso:  psql -d NOMBRE_BASE -f farmacias.sql

CREATE TABLE IF NOT EXISTS farmacias (
    uid       INTEGER PRIMARY KEY,                 -- número único
    nombre    TEXT NOT NULL,                       -- nombre de la farmacia
    direccion TEXT NOT NULL,
    lat       DOUBLE PRECISION NOT NULL CHECK (lat  BETWEEN -90  AND 90),
    long      DOUBLE PRECISION NOT NULL CHECK (long BETWEEN -180 AND 180),
    horario   TEXT
);

INSERT INTO farmacias (uid, nombre, direccion, lat, long, horario) VALUES
 (1,  'Medicity Puembo',                          'Manuel Burbano, Puembo',                                         -0.1774634, -78.3588022, 'Lun-vie 8:00-20:30; sáb y dom 9:00-19:00'),
 (2,  'Farmacias Económicas Puembo Centro',       'Simón Bolívar y 24 de Mayo, Puembo',                             -0.1786097, -78.3589010, NULL),
 (3,  'Farmacias Económicas Puembo',              '24 de Mayo y Humberto Duque, Puembo',                            -0.1984982, -78.3680239, 'Lun-vie 8:00-20:00; sáb y dom 10:00-19:00'),
 (4,  'Medicity Puembo 24 de Mayo',               '24 de Mayo y Patricio Romero, Puembo',                           -0.1998237, -78.3676522, 'Lun-vie 7:00-21:30; sáb y dom 8:00-21:00'),
 (5,  'Farmacia Económica Yaruquí',               'Av. Amazonas S1-41, Yaruquí',                                    -0.1624381, -78.3200072, 'Lun-sáb 7:00-21:00; dom 8:00-20:00'),
 (6,  'Farmacias Medicity Vía Pifo',              'Av. Guayasamín y Ruta Viva, Puembo/Tumbaco',                     -0.2105018, -78.3643521, 'Lun-vie 8:00-21:00; sáb y dom 8:00-20:00'),
 (7,  'Farmacias Económicas Tumbaco Villavega',   'Villa Vega y Av. Guayasamín, Tumbaco',                           -0.2097980, -78.3868623, 'Lun-sáb 8:00-21:00; dom 8:00-20:00'),
 (8,  'Farmacias Económicas Pifo Chaupimolino',   'Chaupimolino, Pifo',                                             -0.2196237, -78.3388996, 'Lun-vie 7:00-21:00; sáb y dom 8:00-20:00'),
 (9,  'Farmacias Medicity Central Tumbaco',       'Juan Montalvo entre Guayaquil y Fray Gonzalo de Vera, Tumbaco',  -0.2135730, -78.4056652, 'Lun-vie 7:30-21:00; sáb 7:30-20:30; dom 7:30-19:30'),
 (10, 'Farmacias Medicity Tumbaco La Cerámica',   'La Cerámica, Tumbaco',                                           -0.2211377, -78.3929391, 'Lun-vie 8:00-21:00; sáb y dom 9:00-20:00'),
 (11, 'Farmacia Económica Pifo Gonzalo Pizarro',  'Gonzalo Pizarro, Pifo',                                          -0.2242182, -78.3407142, 'Lun-vie 6:30-21:00; sáb 7:30-21:00; dom 7:30-20:00')
ON CONFLICT (uid) DO UPDATE SET
    nombre = EXCLUDED.nombre, direccion = EXCLUDED.direccion,
    lat = EXCLUDED.lat, long = EXCLUDED.long, horario = EXCLUDED.horario;
