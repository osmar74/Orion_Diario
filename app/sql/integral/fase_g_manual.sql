USE [Aster_Integral_Api]
GO

SET NOCOUNT ON;

DECLARE @Fecha DATE = '{fecha_sql}';
DECLARE @EntidadesLista NVARCHAR(MAX) = '{entidades_csv}';

DECLARE @FechaInicio DATETIME = CAST(@Fecha AS DATETIME);
DECLARE @FechaFin DATETIME = DATEADD(DAY, 1, @FechaInicio);

IF OBJECT_ID('tempdb..#FiltroEntidades') IS NOT NULL
    DROP TABLE #FiltroEntidades;

SELECT LTRIM(RTRIM(CAST(value AS VARCHAR(128)))) AS Entidad
INTO #FiltroEntidades
FROM STRING_SPLIT(@EntidadesLista, ',')
WHERE LTRIM(RTRIM(value)) <> '';

WITH Comentarios_Filtrados AS (
    SELECT c.[data], c.fecha, c.resultado1, c.resultado2, c.datapers, c.usuario, c.datafijos, c.telefono, c.entidad
    FROM [Aster_Integral_Api].[Integral].[comentarios] c
    INNER JOIN #FiltroEntidades f ON c.entidad = f.Entidad
    WHERE c.fecha >= @FechaInicio
      AND c.fecha < @FechaFin
),
Duracion_Filtrada AS (
    SELECT d.[data], d.fecha_hora, d.entidad, d.tiempo_gestion
    FROM [Integral].[detalle_duracion] d
    INNER JOIN #FiltroEntidades f ON d.entidad = f.Entidad
    WHERE d.fecha_hora >= @FechaInicio
      AND d.fecha_hora < @FechaFin
),
Datos_Procesados AS (
    SELECT
        _comentario.[data] AS [Cliente Nro.],
        FORMAT(_comentario.fecha, 'dd/MM/yyyy') AS [Fecha De Gestion],
        ISNULL(CONVERT(VARCHAR(8), _comentario.fecha, 108), '00:00:00') AS [Hora De Gestion],
        FORMAT(DATEADD(SECOND, COALESCE(TRY_CAST(_duracion.tiempo_gestion AS INT), 0), 0), 'HH:mm:ss') AS [Duracion llamada],
        LTRIM(RTRIM(
            CASE
                WHEN LTRIM(RTRIM(_comentario.resultado1)) IS NULL OR LTRIM(RTRIM(_comentario.resultado1)) = '' THEN ''
                WHEN _comentario.resultado1 IS NOT NULL THEN [Integral].[Obtener_Estado](_comentario.resultado1, _comentario.resultado2)
            END
        )) AS [Desc_Gestion],
        CASE
            WHEN CHARINDEX('compromisos<=>', _comentario.datapers) > 0 THEN
                REPLACE(
                    SUBSTRING(
                        _comentario.datapers,
                        CHARINDEX('compromisos<=>', _comentario.datapers) + LEN('compromisos<=>'),
                        CASE
                            WHEN CHARINDEX('###', _comentario.datapers, CHARINDEX('compromisos<=>', _comentario.datapers)) > 0
                            THEN CHARINDEX('###', _comentario.datapers, CHARINDEX('compromisos<=>', _comentario.datapers)) - (CHARINDEX('compromisos<=>', _comentario.datapers) + LEN('compromisos<=>'))
                            ELSE 10
                        END
                    ),
                    '-', '/'
                )
            ELSE ''
        END AS Fecha_Compromiso,
        [Integral].[Obtener_Usuario](_comentario.usuario) AS Grabador,
        'Vencorp' AS [Responsable De Cobro],
        CASE
            WHEN CHARINDEX('tels<=>', _comentario.datafijos) > 0 THEN
                SUBSTRING(
                    _comentario.datafijos,
                    CHARINDEX('tels<=>', _comentario.datafijos) + LEN('tels<=>'),
                    CASE
                        WHEN CHARINDEX('|', _comentario.datafijos, CHARINDEX('tels<=>', _comentario.datafijos)) > 0
                        THEN CHARINDEX('|', _comentario.datafijos, CHARINDEX('tels<=>', _comentario.datafijos)) - (CHARINDEX('tels<=>', _comentario.datafijos) + LEN('tels<=>'))
                        ELSE 8
                    END
                )
            ELSE ''
        END AS Telefonos,
        _comentario.telefono AS Telefonos_2,
        '' AS [Tipo Cartera],
        _comentario.usuario AS Asesor,
        '' AS [Antiguedad De La Cartera],
        CASE WHEN _comentario.resultado1 IS NULL OR _comentario.resultado1 = '' THEN 'codmaquina' ELSE 'TEL' END AS [Clase de Gestion],
        LEFT(LTRIM(RTRIM([Integral].[Obtener_Causal_Mora](_comentario.resultado2))), 100) AS [Causal de Mora/Respuesta]
    FROM Comentarios_Filtrados _comentario
    LEFT JOIN Duracion_Filtrada _duracion
        ON _comentario.[data] = _duracion.[data]
        AND _comentario.entidad = _duracion.entidad
        AND FORMAT(_comentario.fecha, 'dd/MM/yyyy') = FORMAT(_duracion.fecha_hora, 'dd/MM/yyyy')
        AND ISNULL(CONVERT(VARCHAR(8), _comentario.fecha, 108), '00:00:00') = ISNULL(CONVERT(VARCHAR(8), _duracion.fecha_hora, 108), '00:00:00')
)
SELECT
    [Cliente Nro.], [Fecha De Gestion], [Hora De Gestion], [Duracion llamada],
    [Desc_Gestion] AS [Descripcion Codigo De Gestion],
    Fecha_Compromiso, Grabador, [Responsable De Cobro], Telefonos, Telefonos_2,
    [Tipo Cartera], Asesor, [Antiguedad De La Cartera],
    [Desc_Gestion] AS [Nota de la Gestion],
    [Clase de Gestion], [Causal de Mora/Respuesta]
FROM Datos_Procesados;

DROP TABLE #FiltroEntidades;
