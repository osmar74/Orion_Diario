DECLARE @fecha_sql date = '{fecha_sql}';

SELECT TOP (3) *
FROM [{schema}].[{table}]
WHERE [{date_column}] >= @fecha_sql
  AND [{date_column}] < DATEADD(day, 1, @fecha_sql)
  {entity_filter}
ORDER BY [{date_column}] DESC;
