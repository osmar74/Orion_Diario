DELETE FROM Integral.comentarios
WHERE CONVERT(date, fecha) = ?
  AND entidad = ?;