SELECT DISTINCT entidad, COUNT(*) AS total_registros
FROM comentarios
WHERE DATE(fecha) >= %s
  AND (entidad LIKE %s OR entidad LIKE %s)
GROUP BY entidad
ORDER BY total_registros DESC, entidad ASC;
