-- Integral Diario v2 / Fase D: Obtener entidades SQL para comparar contra archivo
-- Optimizado para SQL Server: no usar CAST(fecha AS date) en WHERE.

DECLARE @fecha_sql date = '{fecha_sql}';

SELECT
    entidad,
    @fecha_sql AS fecha,
    COUNT_BIG(1) AS registros
FROM dbo.comentarios
WHERE fecha >= @fecha_sql
  AND fecha < DATEADD(day, 1, @fecha_sql)
  AND (
        entidad LIKE '%reven%'
        OR entidad LIKE '%anual%'
      )
GROUP BY entidad
ORDER BY registros DESC, entidad ASC;
