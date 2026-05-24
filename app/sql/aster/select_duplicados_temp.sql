SELECT TOP ({limite})
    {columnas_select}
FROM {tabla_origen} t
INNER JOIN {tabla_temp} k
    ON {join_sql}