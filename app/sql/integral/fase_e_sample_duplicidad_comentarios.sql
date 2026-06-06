DECLARE @fecha_sql date = '{fecha_sql}';

SELECT TOP (3) *
FROM integral.comentarios
WHERE fecha >= @fecha_sql
  AND fecha < DATEADD(day, 1, @fecha_sql)
  AND entidad IN ({entidades_sql})
ORDER BY fecha DESC;
