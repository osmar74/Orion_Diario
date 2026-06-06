SELECT entidad, COUNT(*) AS registros
FROM dbo.comentarios
WHERE CONVERT(date, fecha) >= ?
  AND (LOWER(entidad) LIKE '%reven%' OR LOWER(entidad) LIKE '%anual%')
GROUP BY entidad
ORDER BY registros DESC;
