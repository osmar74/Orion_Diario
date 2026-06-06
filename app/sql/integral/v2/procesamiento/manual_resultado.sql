USE [Aster_Integral_Api]
GO

SET NOCOUNT ON;

-- 1. DECLARACIÓN DEL PARÁMETRO COMO VARIABLE LOCAL
-- Cambia aquí la fecha que necesites consultar antes de ejecutar
DECLARE @Fecha DATE;
SET @Fecha = ?; 

-- 2. CTE para filtrar y limpiar la tabla de comentarios (Quitamos el "DISTINCT *")
WITH Comentarios_Filtrados AS (
    SELECT 
        [data], 
        fecha, 
        resultado1, 
        resultado2, 
        datapers, 
        usuario, 
        datafijos, 
        telefono, 
        entidad
    FROM [Aster_Integral_Api].[Integral].[comentarios]
    WHERE CAST(fecha AS DATE) = @Fecha 
),

-- 3. CTE para filtrar y limpiar la tabla de detalle_duracion (Quitamos el "DISTINCT *")
Duracion_Filtrada AS (
    SELECT 
        [data], 
        fecha_hora, 
        entidad, 
        tiempo_gestion
    FROM [Integral].[detalle_duracion]
    WHERE CAST(fecha_hora AS DATE) = @Fecha 
),

-- 4. CTE para procesar y formatear las columnas base
Datos_Procesados AS (
    SELECT 
        _comentario.[data] AS [Cliente Nro.],
        FORMAT(_comentario.fecha, 'dd/MM/yyyy') AS [Fecha De Gestion],
        ISNULL(CONVERT(VARCHAR(8), _comentario.fecha, 108), '00:00:00') AS [Hora De Gestion],
        FORMAT(DATEADD(SECOND, COALESCE(TRY_CAST(_duracion.tiempo_gestion AS INT), 0), 0), 'HH:mm:ss') AS [Duracion llamada],
        
        -- Calculamos el Estado una sola vez para evitar llamar la función escalar 2 veces
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
        
        CASE
            WHEN _comentario.resultado1 IS NULL OR _comentario.resultado1 = '' THEN 'codmaquina'
            ELSE 'TEL'
        END AS [Clase de Gestion],
        
        LEFT(LTRIM(RTRIM([Integral].[Obtener_Causal_Mora](_comentario.resultado2))), 100) AS [Causal de Mora/Respuesta]

    FROM Comentarios_Filtrados _comentario 
    LEFT JOIN Duracion_Filtrada _duracion 
        ON _comentario.[data] = _duracion.[data]
        AND _comentario.entidad = _duracion.entidad
        AND FORMAT(_comentario.fecha, 'dd/MM/yyyy') = FORMAT(_duracion.fecha_hora, 'dd/MM/yyyy')
        AND ISNULL(CONVERT(VARCHAR(8), _comentario.fecha, 108), '00:00:00') = ISNULL(CONVERT(VARCHAR(8), _duracion.fecha_hora, 108), '00:00:00')
)

-- 5. SELECCIÓN FINAL DIRECTA A LA PANTALLA
SELECT 
    [Cliente Nro.], 
    [Fecha De Gestion], 
    [Hora De Gestion], 
    [Duracion llamada],
    [Desc_Gestion] AS [Descripcion Codigo De Gestion],
    Fecha_Compromiso, 
    Grabador, 
    [Responsable De Cobro], 
    Telefonos, 
    Telefonos_2,
    [Tipo Cartera], 
    Asesor, 
    [Antiguedad De La Cartera],
    [Desc_Gestion] AS [Nota de la Gestion], 
    [Clase de Gestion], 
    [Causal de Mora/Respuesta]
FROM Datos_Procesados;
