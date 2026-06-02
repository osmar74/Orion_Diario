SELECT *
FROM dbo.comentarios
WHERE CONVERT(date, fecha) = ?
  AND entidad = ?;
