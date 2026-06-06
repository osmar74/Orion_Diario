DECLARE @fecha_sql date = '{fecha_sql}';

SELECT *
FROM dbo.comentarios
WHERE fecha >= @fecha_sql
  AND fecha < DATEADD(day, 1, @fecha_sql)
  AND entidad IN ({entidades_sql});
