SELECT COUNT(*) AS total
FROM comentarios
WHERE DATE(fecha) = %s
  AND entidad IN ({placeholders})
  AND COALESCE(TRIM(usuario), '') <> 'SystemUser'
