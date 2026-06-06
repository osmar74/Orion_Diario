SELECT
    entidad,
    COUNT(*) AS total_registros
FROM dbo.comentarios
WHERE CONVERT(date, fecha) >= ?
  AND (entidad LIKE ? OR entidad LIKE ?)
GROUP BY entidad
ORDER BY total_registros DESC, entidad ASC;
