SELECT
    c.name AS columna,
    TYPE_NAME(c.user_type_id) AS tipo_sql,
    c.max_length AS longitud,
    c.precision AS precision,
    c.scale AS escala,
    c.is_nullable AS is_nullable,
    c.is_identity AS is_identity
FROM sys.columns c
INNER JOIN sys.objects o
    ON c.object_id = o.object_id
INNER JOIN sys.schemas s
    ON o.schema_id = s.schema_id
WHERE s.name = ?
  AND o.name = ?
ORDER BY c.column_id;
