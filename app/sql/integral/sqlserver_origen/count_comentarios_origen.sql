SELECT COUNT(*) AS total
FROM dbo.comentarios
WHERE CONVERT(date, fecha) = ?
  AND entidad = ?;
