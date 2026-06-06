SELECT *
FROM dbo.comentarios
WHERE CONVERT(date, fecha) = ?
  AND entidad = ?
  AND COALESCE(LTRIM(RTRIM(usuario)), '') <> 'SystemUser';
