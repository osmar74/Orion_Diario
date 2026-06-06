DECLARE @fecha_sql date = '{fecha_sql}';

SELECT COUNT_BIG(1) AS total
FROM [{schema}].[{table}]
WHERE [{date_column}] >= @fecha_sql
  AND [{date_column}] < DATEADD(day, 1, @fecha_sql)
  {entity_filter};
