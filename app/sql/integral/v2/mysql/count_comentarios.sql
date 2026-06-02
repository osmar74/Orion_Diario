SELECT COUNT(*) AS total
FROM comentarios
WHERE DATE(fecha) = %s
  AND entidad = %s;
