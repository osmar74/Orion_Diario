SELECT *
FROM comentarios
WHERE DATE(fecha) = %s
  AND entidad = %s;
