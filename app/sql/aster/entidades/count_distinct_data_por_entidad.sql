SELECT
    entidad,
    COUNT(DISTINCT data) AS numero
FROM comentarios
WHERE DATE(fecha) = %s
GROUP BY entidad
ORDER BY numero DESC
