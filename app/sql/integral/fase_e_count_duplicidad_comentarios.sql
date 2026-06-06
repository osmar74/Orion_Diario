DECLARE @fecha_sql date = '{fecha_sql}';

SELECT COUNT_BIG(1) AS total
FROM integral.comentarios
WHERE fecha >= @fecha_sql
  AND fecha < DATEADD(day, 1, @fecha_sql)
  AND entidad IN ({entidades_sql});
