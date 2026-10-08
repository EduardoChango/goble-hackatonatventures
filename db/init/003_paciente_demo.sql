-- Paciente del guion de la demo: espejo exacto de tratamiento-app/data.py::seed()
-- IDs fijos: paciente 1, visitas 1-2, receta_item 1-5.

INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess,
                      consentimiento, consentimiento_en, lat, lng)
VALUES (1, 'Luis Mora (ejemplo)', (CURRENT_DATE - INTERVAL '72 years 4 months')::DATE, 'Hijo/a',
        TRUE, TRUE, now(), -1.2491, -78.6167);

INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES
    (1, 1),  -- Hipertensión
    (1, 2);  -- Diabetes tipo 2

INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES
    (1, '2026-10-17 10:00', 'Control de hipertensión y diabetes');

INSERT INTO visita (id, paciente_id, fecha, origen) VALUES
    (1, 1, '2026-09-12', 'manual'),
    (2, 1, '2026-10-03', 'manual');

INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES
    -- visita 2026-09-12
    (1, 1, 1,   50, 24, 30, '{08:00}'),
    (2, 1, 2,  850, 12, 30, '{08:00,20:00}'),
    -- visita 2026-10-03: Losartán aumenta a 100 mg, Atorvastatina es nuevo
    (3, 2, 1,  100, 24, 30, '{08:00}'),
    (4, 2, 2,  850, 12, 30, '{08:00,20:00}'),
    (5, 2, 3,   20, 24, 30, '{21:00}');

-- Qué entregó el IESS para la visita 2026-10-03
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES
    (3, 'completo', 30),
    (4, 'parcial',  28),
    (5, 'no',        0);

-- Tomas de hoy: "Losartán@08:00" y "Metformina@08:00"
INSERT INTO toma (receta_item_id, fecha, hora, tomada_en) VALUES
    (3, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:04'),
    (4, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:04');
