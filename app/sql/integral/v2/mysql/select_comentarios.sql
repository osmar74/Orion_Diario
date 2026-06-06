SELECT *
FROM comentarios
WHERE DATE(fecha) = %s
  AND entidad = %s
  AND COALESCE(TRIM(usuario), '') <> 'SystemUser';
