DECLARE @fecha_sql date = '{fecha_sql}';

DELETE FROM [{schema}].[{table}]
WHERE [{date_column}] >= @fecha_sql
  AND [{date_column}] < DATEADD(day, 1, @fecha_sql)
  {entity_filter};
