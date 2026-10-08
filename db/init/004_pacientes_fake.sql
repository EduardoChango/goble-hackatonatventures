-- GENERADO por db/gen_pacientes_fake.py. No editar a mano: edita el script y regenera.
-- 10 pacientes fake (ids 2-11), uno por cada caso de la app.

-- @paciente 2
-- ---------- Paciente 2: Sin IESS: compra todo ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng) VALUES (2, 'Carmen Pazmiño (ejemplo)', '1978-08-08', 'Nieto/a', FALSE, TRUE, now(), -0.1886, -78.3917);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (2, 1), (2, 3);
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (2, CURRENT_DATE + 6 + TIME '11:30', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (100, 2, CURRENT_DATE - 12, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1000, 100, 5, 10, 12, 30, '{08:00,20:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1001, 100, 3, 20, 24, 30, '{21:00}');
INSERT INTO toma (receta_item_id, fecha, hora, tomada_en) VALUES (1000, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '31 minutes');
INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, creado_en, mostrado_en) VALUES (2, 'toma', 'Es hora de tu medicina', '08:00 · Enalapril 10 mg', 'Es hora de tu medicina de las 08:00.', '/plan', to_char(CURRENT_DATE, 'YYYY-MM-DD') || '|Enalapril@08:00|toma', CURRENT_DATE + TIME '08:00', CURRENT_DATE + TIME '08:00');

-- @paciente 3
-- ---------- Paciente 3: IESS entregó todo (todo al día) ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng) VALUES (3, 'Gloria Sánchez (ejemplo)', '1961-04-13', 'Nieto/a', TRUE, TRUE, now(), -0.1737, -78.3377);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (3, 1);
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (3, CURRENT_DATE + 15 + TIME '15:00', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (101, 3, CURRENT_DATE - 40, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1002, 101, 1, 50, 24, 30, '{08:00}');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (102, 3, CURRENT_DATE - 8, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1003, 102, 1, 50, 24, 30, '{08:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1004, 102, 4, 5, 24, 30, '{08:00}');
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES (1003, 'completo', 30), (1004, 'completo', 30);
INSERT INTO toma (receta_item_id, fecha, hora, tomada_en) VALUES (1003, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '21 minutes'), (1004, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '34 minutes');
INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, creado_en, mostrado_en) VALUES (3, 'toma', 'Es hora de tu medicina', '08:00 · Losartán 50 mg', 'Es hora de tu medicina de las 08:00.', '/plan', to_char(CURRENT_DATE, 'YYYY-MM-DD') || '|Losartán@08:00|toma', CURRENT_DATE + TIME '08:00', CURRENT_DATE + TIME '08:00');

-- @paciente 4
-- ---------- Paciente 4: IESS aún no responde ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng) VALUES (4, 'Teresa Toapanta (ejemplo)', '1959-05-15', NULL, TRUE, TRUE, now(), -0.1803, -78.3578);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (4, 2);
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (4, CURRENT_DATE + 12 + TIME '08:30', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (103, 4, CURRENT_DATE - 35, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1005, 103, 2, 850, 12, 30, '{08:00,20:00}');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (104, 4, CURRENT_DATE - 1, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1006, 104, 2, 850, 12, 30, '{08:00,20:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1007, 104, 6, 5, 24, 30, '{08:00}');
INSERT INTO toma (receta_item_id, fecha, hora, tomada_en) VALUES (1007, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '29 minutes');
INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, creado_en, mostrado_en) VALUES (4, 'toma', 'Es hora de tu medicina', '08:00 · Metformina 850 mg', 'Es hora de tu medicina de las 08:00.', '/plan', to_char(CURRENT_DATE, 'YYYY-MM-DD') || '|Metformina@08:00|toma', CURRENT_DATE + TIME '08:00', CURRENT_DATE + TIME '08:00');

-- @paciente 5
-- ---------- Paciente 5: Primera visita ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng) VALUES (5, 'Teresa Masaquiza (ejemplo)', '1968-02-13', 'Hijo/a', TRUE, TRUE, now(), -0.1353, -78.3632);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (5, 3);
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (5, CURRENT_DATE + 16 + TIME '15:00', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (105, 5, CURRENT_DATE - 5, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1008, 105, 3, 40, 24, 30, '{21:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1009, 105, 8, 20, 24, 30, '{08:00}');
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES (1008, 'no', 0), (1009, 'completo', 30);
INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, creado_en, mostrado_en) VALUES (5, 'toma', 'Es hora de tu medicina', '21:00 · Atorvastatina 40 mg', 'Es hora de tu medicina de las 21:00.', '/plan', to_char(CURRENT_DATE, 'YYYY-MM-DD') || '|Atorvastatina@21:00|toma', CURRENT_DATE + TIME '21:00', CURRENT_DATE + TIME '21:00');

-- @paciente 6
-- ---------- Paciente 6: Medicamento suspendido ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng) VALUES (6, 'Carmen Villacís (ejemplo)', '1979-08-13', 'Hermano/a', TRUE, TRUE, now(), -0.1338, -78.381);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (6, 1);
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (6, CURRENT_DATE + 21 + TIME '11:30', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (106, 6, CURRENT_DATE - 33, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1010, 106, 1, 50, 24, 30, '{08:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1011, 106, 4, 10, 24, 30, '{08:00}');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (107, 6, CURRENT_DATE - 3, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1012, 107, 1, 100, 24, 30, '{08:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1013, 107, 5, 10, 24, 30, '{08:00}');
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES (1012, 'completo', 30), (1013, 'completo', 30);
INSERT INTO toma (receta_item_id, fecha, hora, tomada_en) VALUES (1012, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '1 minutes'), (1013, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '8 minutes');
INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, creado_en, mostrado_en) VALUES (6, 'toma', 'Es hora de tu medicina', '08:00 · Losartán 100 mg', 'Es hora de tu medicina de las 08:00.', '/plan', to_char(CURRENT_DATE, 'YYYY-MM-DD') || '|Losartán@08:00|toma', CURRENT_DATE + TIME '08:00', CURRENT_DATE + TIME '08:00');

-- @paciente 7
-- ---------- Paciente 7: Dosis reducida ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng) VALUES (7, 'Blanca Sánchez (ejemplo)', '1944-12-17', NULL, TRUE, TRUE, now(), -0.1356, -78.3903);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (7, 2);
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (7, CURRENT_DATE + 16 + TIME '11:30', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (108, 7, CURRENT_DATE - 30, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1014, 108, 2, 1000, 12, 30, '{08:00,20:00}');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (109, 7, CURRENT_DATE - 6, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1015, 109, 2, 500, 12, 30, '{08:00,20:00}');
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES (1015, 'parcial', 40);
INSERT INTO toma (receta_item_id, fecha, hora, tomada_en) VALUES (1015, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '14 minutes');
INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, creado_en, mostrado_en) VALUES (7, 'toma', 'Es hora de tu medicina', '08:00 · Metformina 500 mg', 'Es hora de tu medicina de las 08:00.', '/plan', to_char(CURRENT_DATE, 'YYYY-MM-DD') || '|Metformina@08:00|toma', CURRENT_DATE + TIME '08:00', CURRENT_DATE + TIME '08:00');

-- @paciente 8
-- ---------- Paciente 8: Cambio de frecuencia (24 h -> 12 h) ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng) VALUES (8, 'Galo Cevallos (ejemplo)', '1948-11-23', NULL, TRUE, TRUE, now(), -0.1614, -78.3683);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (8, 2), (8, 1);
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (8, CURRENT_DATE + 11 + TIME '15:00', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (110, 8, CURRENT_DATE - 31, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1016, 110, 2, 850, 24, 30, '{08:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1017, 110, 1, 50, 24, 30, '{08:00}');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (111, 8, CURRENT_DATE - 4, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1018, 111, 2, 850, 12, 30, '{08:00,20:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1019, 111, 1, 50, 24, 30, '{08:00}');
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES (1018, 'completo', 60), (1019, 'completo', 30);
INSERT INTO toma (receta_item_id, fecha, hora, tomada_en) VALUES (1018, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '19 minutes'), (1019, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '32 minutes');
INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, creado_en, mostrado_en) VALUES (8, 'toma', 'Es hora de tu medicina', '08:00 · Metformina 850 mg', 'Es hora de tu medicina de las 08:00.', '/plan', to_char(CURRENT_DATE, 'YYYY-MM-DD') || '|Metformina@08:00|toma', CURRENT_DATE + TIME '08:00', CURRENT_DATE + TIME '08:00');

-- @paciente 9
-- ---------- Paciente 9: Compró en farmacia lo que faltaba ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng) VALUES (9, 'Marlene Masaquiza (ejemplo)', '1971-07-14', 'Hijo/a', TRUE, TRUE, now(), -0.1766, -78.3466);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (9, 1);
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (9, CURRENT_DATE + 4 + TIME '09:00', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (112, 9, CURRENT_DATE - 10, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1020, 112, 1, 100, 24, 30, '{08:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1021, 112, 4, 5, 24, 30, '{08:00}');
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES (1020, 'parcial', 15), (1021, 'completo', 30);
INSERT INTO compra (id, paciente_id, visita_id, farmacia_id, modo) VALUES (1, 9, 112, 7, 'envio');
INSERT INTO compra_item (compra_id, receta_item_id, unidades) VALUES (1, 1020, 15);
INSERT INTO toma (receta_item_id, fecha, hora, tomada_en) VALUES (1020, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '38 minutes');
INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, creado_en, mostrado_en) VALUES (9, 'toma', 'Es hora de tu medicina', '08:00 · Losartán 100 mg', 'Es hora de tu medicina de las 08:00.', '/plan', to_char(CURRENT_DATE, 'YYYY-MM-DD') || '|Losartán@08:00|toma', CURRENT_DATE + TIME '08:00', CURRENT_DATE + TIME '08:00');

-- @paciente 10
-- ---------- Paciente 10: Sin consentimiento (perfil incompleto) ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng) VALUES (10, 'Galo Toapanta (ejemplo)', '1974-08-12', NULL, TRUE, FALSE, NULL, -0.1335, -78.3809);
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (10, CURRENT_DATE + 18 + TIME '11:30', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (113, 10, CURRENT_DATE - 9, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1022, 113, 7, 50, 24, 30, '{06:00}');
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES (1022, 'completo', 30);
INSERT INTO toma (receta_item_id, fecha, hora, tomada_en) VALUES (1022, CURRENT_DATE, '06:00', CURRENT_DATE + TIME '06:00' + INTERVAL '31 minutes');
INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, creado_en, mostrado_en) VALUES (10, 'toma', 'Es hora de tu medicina', '06:00 · Levotiroxina 50 mg', 'Es hora de tu medicina de las 06:00.', '/plan', to_char(CURRENT_DATE, 'YYYY-MM-DD') || '|Levotiroxina@06:00|toma', CURRENT_DATE + TIME '06:00', CURRENT_DATE + TIME '06:00');

-- @paciente 11
-- ---------- Paciente 11: Caso cargado: 5 medicamentos, receta leída con IA ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng) VALUES (11, 'Teresa Lozada (ejemplo)', '1968-09-22', 'Nieto/a', TRUE, TRUE, now(), -0.1344, -78.3466);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (11, 1), (11, 2), (11, 3), (11, 5);
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (11, CURRENT_DATE + 17 + TIME '08:30', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (114, 11, CURRENT_DATE - 36, 'manual', NULL);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1023, 114, 1, 50, 24, 30, '{08:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1024, 114, 2, 850, 12, 30, '{08:00,20:00}');
INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES (115, 11, CURRENT_DATE - 2, 'ia', '{"origen": "ia", "modelo": "claude-sonnet-5-5", "medicamentos": [{"nombre": "LOSARTÁN TABLETAS", "dosis_mg": 100, "cada_horas": 24, "dias": 30}, {"nombre": "METFORMINA", "dosis_mg": 1000, "cada_horas": 12, "dias": 30}, {"nombre": "ATORVASTATINA TABLETAS", "dosis_mg": 20, "cada_horas": 24, "dias": 30}, {"nombre": "GLIBENCLAMIDA", "dosis_mg": 5, "cada_horas": 24, "dias": null}, {"nombre": "OMEPRAZOL TABLETAS", "dosis_mg": 20, "cada_horas": 24, "dias": 30}]}'::jsonb);
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1025, 115, 1, 100, 24, 30, '{08:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1026, 115, 2, 1000, 12, 30, '{08:00,20:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1027, 115, 3, 20, 24, 30, '{21:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1028, 115, 6, 5, 24, 30, '{08:00}');
INSERT INTO receta_item (id, visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios) VALUES (1029, 115, 8, 20, 24, 30, '{08:00}');
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES (1025, 'completo', 30), (1026, 'parcial', 30), (1027, 'no', 0), (1028, 'completo', 30), (1029, 'no', 0);
INSERT INTO toma (receta_item_id, fecha, hora, tomada_en) VALUES (1025, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '32 minutes'), (1026, CURRENT_DATE, '08:00', CURRENT_DATE + TIME '08:00' + INTERVAL '11 minutes');
INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, creado_en, mostrado_en) VALUES (11, 'toma', 'Es hora de tu medicina', '08:00 · Losartán 100 mg', 'Es hora de tu medicina de las 08:00.', '/plan', to_char(CURRENT_DATE, 'YYYY-MM-DD') || '|Losartán@08:00|toma', CURRENT_DATE + TIME '08:00', CURRENT_DATE + TIME '08:00');
INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url) VALUES (11, 'compra', 'Falta comprar medicinas', 'Te falta: Atorvastatina, Omeprazol.', 'Tienes medicinas pendientes por comprar.', '/farmacias');
