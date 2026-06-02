SELECT COUNT(1) AS total
FROM dbo.comentarios
WHERE CONVERT(date, fecha) = ?
  AND entidad = ?;
