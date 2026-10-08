-- Los seeds insertan IDs explícitos: alinear las secuencias IDENTITY para que
-- los próximos INSERT de la app no choquen con esos IDs.
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['promocion', 'condicion',
                             'cuidador', 'producto', 'regla_sugerencia', 'paciente', 'usuario', 'cita', 'visita', 'receta_item', 'compra', 'toma', 'aviso']
    LOOP
        EXECUTE format(
            'SELECT setval(pg_get_serial_sequence(%L, ''id''), COALESCE((SELECT max(id) FROM %I), 0) + 1, false)',
            t, t);
    END LOOP;
END $$;
