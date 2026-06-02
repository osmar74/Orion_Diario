SELECT COUNT(1) AS total
FROM Integral.comentarios
WHERE CONVERT(date, fecha) = ?
  AND entidad = ?;
