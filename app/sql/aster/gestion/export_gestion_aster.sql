WITH
CTE_Aster_Base AS (
    SELECT
        Codigo,
        Fecha_Hora,
        Duracion,
        Estado,
        Atendio,
        Numero,
        Cartera,
        CASE
            WHEN Estado = 'ATENDIDO'
             AND Atendio IN ('HUMANO', 'DESCONOCIDO')
            THEN 1 ELSE 0
        END AS EsHumano
    FROM [dbo].[aster_dia_nc]
    WHERE Fecha_Hora >= ? AND Fecha_Hora < ?
),

CTE_Comentarios_Base AS (
    SELECT
        [data],
        resultado1,
        resultado2,
        datapers,
        usuario,
        comentario
    FROM [dbo].[comentarios]
    WHERE fecha >= ? AND fecha < ?
),

CTE_Maquinas AS (
    SELECT DISTINCT
        Codigo AS Cliente_Nro,
        Fecha_Hora,
        Duracion,
        CASE
            WHEN Estado = 'OCUPADO' AND Atendio = 'NULL' THEN 'Telefono Ocupado'
            WHEN Estado = 'ATENDIDO' AND Atendio = 'CONTESTADOR' THEN 'Buzon de voz'
            WHEN Estado = 'NO ATENDIDO' AND Atendio = 'NULL' THEN 'No contestan'
            WHEN Estado = 'ATENDIDO' AND Atendio = 'CORTO' THEN 'No contestan'
            WHEN Estado = 'CONGESTION' AND Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
            WHEN Estado = 'SIN CANALES' AND Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
            ELSE 'Usuario pide volver a llamar'
        END AS [Descripcion Codigo De Gestion],
        '' AS Fecha_Compromiso,
        '' AS Grabador,
        Numero AS Telefonos,
        CASE
            WHEN Codigo IS NULL OR LTRIM(RTRIM(Codigo)) = '' THEN NULL
            WHEN Codigo LIKE 'M%' THEN 'Mobile'
            ELSE 'Home'
        END AS [Tipo Cartera],
        '' AS Asesor,
        Cartera AS [Antiguedad De La Cartera],
        '' AS [Nota de la Gestion],
        'codmaquina' AS [Clase de Gestion],
        '' AS [Causal de Mora/Respuesta]
    FROM CTE_Aster_Base
    WHERE EsHumano = 0
),

CTE_Humanos_Processed AS (
    SELECT
        _dia.Codigo AS Cliente_Nro,
        _dia.Fecha_Hora,
        _dia.Duracion,
        _dia.Numero AS Telefonos,
        _dia.Cartera AS [Antiguedad De La Cartera],
        CASE
            WHEN _contactada.resultado1 IS NULL
              OR LTRIM(RTRIM(_contactada.resultado1)) = ''
            THEN 'codmaquina'
            ELSE 'TEL'
        END AS [Clase de Gestion],

        LTRIM(RTRIM(CASE
            WHEN _contactada.resultado1 IS NULL
              OR LTRIM(RTRIM(_contactada.resultado1)) = ''
            THEN
                CASE
                    WHEN _dia.Estado = 'OCUPADO' AND _dia.Atendio = 'NULL' THEN 'Telefono Ocupado'
                    WHEN _dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'CONTESTADOR' THEN 'Buzon de voz'
                    WHEN _dia.Estado = 'NO ATENDIDO' AND _dia.Atendio = 'NULL' THEN 'No contestan'
                    WHEN _dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'CORTO' THEN 'No contestan'
                    WHEN _dia.Estado = 'CONGESTION' AND _dia.Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                    WHEN _dia.Estado = 'SIN CANALES' AND _dia.Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                    ELSE 'Usuario pide volver a llamar'
                END
            ELSE [dbo].[Obtener_Estado](_contactada.resultado1, _contactada.resultado2)
        END)) AS [Desc_Raw],

        CASE
            WHEN CHARINDEX('compromisos<=>', _contactada.datapers) > 0 THEN
                REPLACE(
                    SUBSTRING(
                        _contactada.datapers,
                        CHARINDEX('compromisos<=>', _contactada.datapers) + 14,
                        CASE
                            WHEN CHARINDEX('###', _contactada.datapers, CHARINDEX('compromisos<=>', _contactada.datapers)) > 0
                            THEN CHARINDEX('###', _contactada.datapers, CHARINDEX('compromisos<=>', _contactada.datapers))
                               - (CHARINDEX('compromisos<=>', _contactada.datapers) + 14)
                            ELSE 10
                        END
                    ),
                    '-',
                    '/'
                )
            ELSE ''
        END AS Fecha_Compromiso,

        [dbo].[Obtener_Usuario](_contactada.usuario) AS Grabador,

        CASE
            WHEN _dia.Codigo IS NULL OR LTRIM(RTRIM(_dia.Codigo)) = '' THEN NULL
            WHEN _dia.Codigo LIKE 'M%' THEN 'Mobile'
            ELSE 'Home'
        END AS [Tipo Cartera],

        _contactada.usuario AS Asesor,

        LTRIM(RTRIM(
            REPLACE(
                REPLACE(
                    REPLACE(
                        REPLACE(_contactada.comentario, CHAR(9), ''),
                        CHAR(10),
                        ''
                    ),
                    CHAR(13),
                    ''
                ),
                CHAR(160),
                ' '
            )
        )) AS [Nota_Clean],

        LTRIM(RTRIM([dbo].[Obtener_Causal_Mora](_contactada.resultado2)))
            AS [Causal de Mora/Respuesta]
    FROM CTE_Aster_Base _dia
    LEFT JOIN CTE_Comentarios_Base _contactada
        ON _dia.Codigo = _contactada.[data]
    WHERE _dia.EsHumano = 1
),

CTE_Humanos_Final AS (
    SELECT DISTINCT
        Cliente_Nro,
        Fecha_Hora,
        Duracion,
        CASE
            WHEN [Desc_Raw] = 'Usuario pide volver a llamar'
             AND [Clase de Gestion] = 'codmaquina'
            THEN 'No contestan'
            ELSE [Desc_Raw]
        END AS [Descripcion Codigo De Gestion],
        Fecha_Compromiso,
        Grabador,
        Telefonos,
        [Tipo Cartera],
        Asesor,
        [Antiguedad De La Cartera],
        CASE
            WHEN [Desc_Raw] = 'Usuario pide volver a llamar'
             AND [Clase de Gestion] = 'codmaquina'
            THEN ''
            ELSE [Nota_Clean]
        END AS [Nota de la Gestion],
        [Clase de Gestion],
        [Causal de Mora/Respuesta]
    FROM CTE_Humanos_Processed
),

CTE_Universo AS (
    SELECT * FROM CTE_Maquinas
    UNION ALL
    SELECT * FROM CTE_Humanos_Final
)

SELECT
    Cliente_Nro AS [Cliente Nro.],
    FORMAT(Fecha_Hora, 'dd/MM/yyyy') AS [Fecha De Gestion],
    ISNULL(CONVERT(VARCHAR(8), Fecha_Hora, 108), '00:00:00') AS [Hora De Gestion],
    FORMAT(DATEADD(SECOND, COALESCE(TRY_CAST(Duracion AS INT), 0), 0), 'HH:mm:ss') AS [Duracion llamada],
    [Descripcion Codigo De Gestion],
    Fecha_Compromiso,
    Grabador,
    'Vencorp' AS [Responsable De Cobro],
    Telefonos,
    [Tipo Cartera],
    Asesor,
    [Antiguedad De La Cartera],
    [Nota de la Gestion],
    [Clase de Gestion],
    [Causal de Mora/Respuesta]
FROM CTE_Universo
ORDER BY [Clase de Gestion], [Hora De Gestion]
