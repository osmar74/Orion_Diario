SELECT COUNT(*) AS total
FROM Integral.comentarios
WHERE CONVERT(date, fecha) = ?
  AND entidad = ?;
