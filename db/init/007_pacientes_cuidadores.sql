-- GENERADO por db/gen_pacientes_fake.py (generar_abastecimiento). No editar a mano.
-- Pacientes con movilidad reducida (ids 12-15), sus cuidadores y logins. Contraseña: demo1234

-- Cuidadores (no dependen de un paciente: el reset no los toca)
INSERT INTO cuidador (id, nombre, email, telefono, lat, lng) VALUES
    (1, 'Ana Quishpe (ejemplo)', 'ana.quishpe@demo.ec', '0991111111', -0.212, -78.4),
    (2, 'Diego Andrade (ejemplo)', 'diego.andrade@demo.ec', '0992222222', -0.179, -78.359),
    (3, 'Sofía Paredes (ejemplo)', 'sofia.paredes@demo.ec', '0993333333', -0.1625, -78.3205);

-- @paciente 12
-- ---------- Paciente 12: Jorge Quishpe (ejemplo) ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng, direccion_entrega, movilidad_reducida) VALUES (12, 'Jorge Quishpe (ejemplo)', '1949-03-14', 'Hijo/a', TRUE, TRUE, now(), -0.17, -78.36, 'Calle Manuel Burbano y 24 de Mayo, Puembo', TRUE);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (12, 7);
INSERT INTO paciente_cuidador (paciente_id, cuidador_id, rol, parentesco) VALUES (12, 1, 'principal', 'Hija');
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (12, CURRENT_DATE + 8 + TIME '09:00', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen) VALUES (200, 12, CURRENT_DATE - 24, 'manual');
INSERT INTO receta_item (id, visita_id, uid_medicina, dosis_mg, cada_horas, dias, horarios) VALUES (2000, 200, 'FE-00082', 250, 8, 30, '{06:00,14:00,22:00}');
INSERT INTO receta_item (id, visita_id, uid_medicina, dosis_mg, cada_horas, dias, horarios) VALUES (2001, 200, 'FE-00084', 1, 24, 30, '{08:00}');
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES (2000, 'completo', 90), (2001, 'completo', 30);
INSERT INTO compra (id, paciente_id, visita_id, uid_farmacia, modo) VALUES (200, 12, 200, 1, 'recoger');
INSERT INTO compra_item (compra_id, receta_item_id, unidades) VALUES (200, 2001, 30);
INSERT INTO usuario (id, paciente_id, email, password_hash) VALUES (12, 12, 'jorge.quishpe@demo.ec', 'pbkdf2:sha256:600000$7DfaPuYzO5ZlzlwM$356b46ff832af488f47aee3feba484de7cf13546fc78c95e45783efb73da5e30');

-- @paciente 13
-- ---------- Paciente 13: Rosa Quishpe (ejemplo) ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng, direccion_entrega, movilidad_reducida) VALUES (13, 'Rosa Quishpe (ejemplo)', '1952-07-02', 'Hijo/a', TRUE, TRUE, now(), -0.17, -78.36, 'Calle Manuel Burbano y 24 de Mayo, Puembo', TRUE);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (13, 8), (13, 1);
INSERT INTO paciente_cuidador (paciente_id, cuidador_id, rol, parentesco) VALUES (13, 1, 'principal', 'Hija');
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (13, CURRENT_DATE + 10 + TIME '09:00', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen) VALUES (201, 13, CURRENT_DATE - 10, 'manual');
INSERT INTO receta_item (id, visita_id, uid_medicina, dosis_mg, cada_horas, dias, horarios) VALUES (2002, 201, 'FE-00087', 10, 24, 30, '{21:00}');
INSERT INTO receta_item (id, visita_id, uid_medicina, dosis_mg, cada_horas, dias, horarios) VALUES (2003, 201, 'FE-00088', 10, 12, 30, '{08:00,20:00}');
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES (2002, 'completo', 30), (2003, 'parcial', 20);
INSERT INTO usuario (id, paciente_id, email, password_hash) VALUES (13, 13, 'rosa.quishpe@demo.ec', 'pbkdf2:sha256:600000$rsRNeOQvteq8W07P$7dc287627f40b3e828fabe5e1934c78dde4397bbf7c8245c8bb8ff613a6c4564');

-- @paciente 14
-- ---------- Paciente 14: Patricio Andrade (ejemplo) ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng, direccion_entrega, movilidad_reducida) VALUES (14, 'Patricio Andrade (ejemplo)', '1978-11-20', 'Hermano/a', TRUE, TRUE, now(), -0.199, -78.367, 'Av. Interoceánica km 18, Puembo', TRUE);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (14, 6);
INSERT INTO paciente_cuidador (paciente_id, cuidador_id, rol, parentesco) VALUES (14, 2, 'principal', 'Hermano'), (14, 3, 'apoyo', 'Enfermera');
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (14, CURRENT_DATE + 13 + TIME '09:00', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen) VALUES (202, 14, CURRENT_DATE - 5, 'manual');
INSERT INTO receta_item (id, visita_id, uid_medicina, dosis_mg, cada_horas, dias, horarios) VALUES (2004, 202, 'FE-00103', 300, 8, 30, '{06:00,14:00,22:00}');
INSERT INTO receta_item (id, visita_id, uid_medicina, dosis_mg, cada_horas, dias, horarios) VALUES (2005, 202, 'FE-00177', 5, 12, 30, '{08:00,20:00}');
INSERT INTO receta_item (id, visita_id, uid_medicina, dosis_mg, cada_horas, dias, horarios) VALUES (2006, 202, 'FE-00136', 20, 24, 30, '{07:00}');
INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES (2004, 'completo', 90), (2005, 'completo', 60), (2006, 'completo', 30);
INSERT INTO usuario (id, paciente_id, email, password_hash) VALUES (14, 14, 'patricio.andrade@demo.ec', 'pbkdf2:sha256:600000$BGokU4v1w8ozDyk3$66b40e04b8f15dca38c6638b055041502047eacd5092f0751dd77e5cd8bfe6ce');

-- @paciente 15
-- ---------- Paciente 15: Mercedes Yánez (ejemplo) ----------
INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, consentimiento, consentimiento_en, lat, lng, direccion_entrega, movilidad_reducida) VALUES (15, 'Mercedes Yánez (ejemplo)', '1940-05-09', 'Enfermera', TRUE, TRUE, now(), -0.164, -78.325, 'Calle Amazonas S1-80, Yaruquí', TRUE);
INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES (15, 9);
INSERT INTO paciente_cuidador (paciente_id, cuidador_id, rol, parentesco) VALUES (15, 3, 'principal', 'Enfermera');
INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES (15, CURRENT_DATE + 19 + TIME '09:00', 'Control médico');
INSERT INTO visita (id, paciente_id, fecha, origen) VALUES (203, 15, CURRENT_DATE - 2, 'manual');
INSERT INTO receta_item (id, visita_id, uid_medicina, dosis_mg, cada_horas, dias, horarios) VALUES (2007, 203, 'FE-00150', 50, 8, 30, '{06:00,14:00,22:00}');
INSERT INTO receta_item (id, visita_id, uid_medicina, dosis_mg, cada_horas, dias, horarios) VALUES (2008, 203, 'FE-00144', 500, 8, 30, '{07:00,15:00,23:00}');
INSERT INTO usuario (id, paciente_id, email, password_hash) VALUES (15, 15, 'mercedes.yanez@demo.ec', 'pbkdf2:sha256:600000$x6VYuN1hX24m3Xdu$9cd8ad47ddf97f98d36e64846cd52f1a5e25166870013d27ccfcf7c9f66dcf91');
