/*
FechaFiltro = '2026-05-28', 
@EntidadesLista = 'Discador_Base_Preventivo_27052026,Otra_Base_Campania_2026';
*/
USE [Aster_Integral_Api]
GO

SET NOCOUNT ON;

-- =========================================================================
-- 1. DECLARACIÓN DE VARIABLES LOCALES (PARÁMETROS DEL REPORTE)
--    Modifica estos valores según lo que necesites consultar antes de ejecutar.
-- =========================================================================
DECLARE @FechaFiltro DATE;
SET @FechaFiltro = ?;
DECLARE @EntidadesLista NVARCHAR(MAX);
SET @EntidadesLista = ?;

-- =========================================================================
-- 2. CONFIGURACIÓN DEL ENTORNO Y RANGOS DE FECHA
-- =========================================================================
DECLARE @FechaInicio DATETIME = CAST(@FechaFiltro AS DATETIME);
DECLARE @FechaFin DATETIME = DATEADD(DAY, 1, @FechaInicio);

-- Asegura la eliminación previa de la tabla temporal por si falló una ejecución anterior
IF OBJECT_ID('tempdb..#FiltroEntidades') IS NOT NULL 
    DROP TABLE #FiltroEntidades;

-- Separar las entidades para el JOIN de alta velocidad
SELECT CAST(value AS VARCHAR(128)) AS Entidad 
INTO #FiltroEntidades 
FROM STRING_SPLIT(@EntidadesLista, ',');

-- =========================================================================
-- 3. CONSULTA PRINCIPAL MEDIANTE CTEs
-- =========================================================================
WITH AsterDia_Base AS (
    SELECT 
        Codigo, Fecha_Hora, Duracion, Estado, Atendio, Numero, Cartera
    FROM [Integral].[aster_dia_nc] a
    INNER JOIN #FiltroEntidades f ON a.entidad = f.Entidad
    WHERE a.Fecha_Hora >= @FechaInicio AND a.Fecha_Hora < @FechaFin
),
Bloque1_NoAtendidos AS (
    SELECT 
        _dia.Codigo AS [Cliente Nro.],
        CONVERT(VARCHAR(10), _dia.Fecha_Hora, 103) AS [Fecha De Gestion],
        ISNULL(CONVERT(VARCHAR(8), _dia.Fecha_Hora, 108), '00:00:00') AS [Hora De Gestion],
        CONVERT(VARCHAR(8), DATEADD(SECOND, COALESCE(TRY_CAST(_dia.Duracion AS INT), 0), 0), 108) AS [Duracion llamada],
        CASE
            WHEN _dia.Estado = 'OCUPADO' AND _dia.Atendio = 'NULL' THEN 'Telefono Ocupado'
            WHEN _dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'CONTESTADOR' THEN 'Buzon de voz'
            WHEN _dia.Estado = 'NO ATENDIDO' AND _dia.Atendio = 'NULL' THEN 'No contestan'
            WHEN _dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'CORTO' THEN 'No contestan'
            WHEN _dia.Estado = 'CONGESTION' AND _dia.Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
            WHEN _dia.Estado = 'SIN CANALES' AND _dia.Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
            ELSE 'Usuario pide volver a llamar'
        END AS [Descripcion Codigo De Gestion],
        CAST('' AS VARCHAR(100)) AS Fecha_Compromiso,
        CAST('' AS VARCHAR(100)) AS Grabador, 
        'Vencorp' AS [Responsable De Cobro],
        _dia.Numero AS Telefonos,
        CASE WHEN LEFT(_dia.Codigo, 1) = 'M' THEN 'Mobile' ELSE 'Home' END AS [Tipo Cartera],
        CAST('' AS VARCHAR(100)) AS Asesor,
        _dia.Cartera AS [Antiguedad De La Cartera],
        'codmaquina' AS [Clase de Gestion],
        CAST('' AS VARCHAR(100)) AS [Causal de Mora/Respuesta]
    FROM AsterDia_Base _dia
    WHERE NOT ((_dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'HUMANO') OR (_dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'DESCONOCIDO'))
),
Bloque2_Contactados AS (
    SELECT 
        _dia.Codigo AS Cliente_Nro,
        CONVERT(VARCHAR(10), _dia.Fecha_Hora, 103) AS [Fecha De Gestion],
        ISNULL(CONVERT(VARCHAR(8), _dia.Fecha_Hora, 108), '00:00:00') AS [Hora De Gestion], 
        CONVERT(VARCHAR(8), DATEADD(SECOND, COALESCE(TRY_CAST(_dia.Duracion AS INT), 0), 0), 108) AS [Duracion llamada],
        
        LTRIM(RTRIM(CASE
            WHEN _contactada.resultado1 IS NULL OR LTRIM(RTRIM(_contactada.resultado1)) = '' THEN
                CASE
                    WHEN _dia.Estado = 'OCUPADO' AND _dia.Atendio = 'NULL' THEN 'Telefono Ocupado'
                    WHEN _dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'CONTESTADOR' THEN 'Buzon de voz'
                    WHEN _dia.Estado = 'NO ATENDIDO' AND _dia.Atendio = 'NULL' THEN 'No contestan'
                    WHEN _dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'CORTO' THEN 'No contestan'
                    WHEN _dia.Estado = 'CONGESTION' AND _dia.Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                    WHEN _dia.Estado = 'SIN CANALES' AND _dia.Atendio = 'NULL' THEN 'Telefono Fuera de Servicio'
                    ELSE 'Usuario pide volver a llamar'
                END
            ELSE [Integral].[Obtener_Estado](_contactada.resultado1, _contactada.resultado2)            
        END)) AS [Desc_Gestion],

        CASE 
            WHEN CHARINDEX('compromisos<=>', _contactada.datapers) > 0 THEN
                REPLACE(SUBSTRING(_contactada.datapers, CHARINDEX('compromisos<=>', _contactada.datapers) + 14,
                    CASE WHEN CHARINDEX('###', _contactada.datapers, CHARINDEX('compromisos<=>', _contactada.datapers)) > 0 
                         THEN CHARINDEX('###', _contactada.datapers, CHARINDEX('compromisos<=>', _contactada.datapers)) - (CHARINDEX('compromisos<=>', _contactada.datapers) + 14)
                         ELSE 10 END), '-', '/')
            ELSE ''
        END AS Fecha_Compromiso,
        [Integral].[Obtener_Usuario](_contactada.usuario) AS Grabador,
        'Vencorp' AS [Responsable De Cobro],
        _dia.Numero AS Telefonos,
        CASE 
            WHEN _dia.Codigo IS NULL OR LTRIM(RTRIM(_dia.Codigo)) = '' THEN NULL
            WHEN _dia.Codigo LIKE 'M%' THEN 'Mobile'
            ELSE 'Home'
        END AS [Tipo Cartera],
        _contactada.usuario AS Asesor,
        _dia.Cartera AS [Antiguedad De La Cartera],
        CASE WHEN _contactada.resultado1 IS NULL OR _contactada.resultado1 = '' THEN 'codmaquina' ELSE 'TEL' END AS [Clase de Gestion],
        LTRIM(RTRIM([Integral].[Obtener_Causal_Mora](_contactada.resultado2))) AS [Causal de Mora/Respuesta]
    FROM AsterDia_Base _dia
    LEFT JOIN [Integral].[comentarios] _contactada 
        ON _dia.Codigo = _contactada.[data]
        AND _contactada.fecha >= @FechaInicio AND _contactada.fecha < @FechaFin
        AND _contactada.resultado1 NOT IN ('No Atendido','Atendido') 
        AND _contactada.resultado2 NOT IN ('OCUPADO','ATENDIDO','NO ATENDIDA','CONTESTADOR','SIN CANALES','CONGESTIONADO')
        AND _contactada.entidad IN (SELECT Entidad FROM #FiltroEntidades)
    WHERE ((_dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'HUMANO') OR (_dia.Estado = 'ATENDIDO' AND _dia.Atendio = 'DESCONOCIDO'))
)

-- =========================================================================
-- 4. UNIÓN Y RETORNO FINAL DIRECTO A LA PARRILLA DE RESULTADOS
-- =========================================================================
SELECT 
    [Cliente Nro.], [Fecha De Gestion], [Hora De Gestion], [Duracion llamada],
    [Descripcion Codigo De Gestion], Fecha_Compromiso, Grabador, [Responsable De Cobro], 
    Telefonos, [Tipo Cartera], Asesor, [Antiguedad De La Cartera],
    [Descripcion Codigo De Gestion] AS [Nota de la Gestion],
    [Clase de Gestion], [Causal de Mora/Respuesta]
FROM Bloque1_NoAtendidos

UNION 

SELECT 
    Cliente_Nro AS [Cliente Nro.], [Fecha De Gestion], [Hora De Gestion], [Duracion llamada],
    CASE WHEN [Desc_Gestion] = 'Usuario pide volver a llamar' AND [Clase de Gestion] = 'codmaquina' THEN 'No contestan' ELSE [Desc_Gestion] END AS [Descripcion Codigo De Gestion],
    Fecha_Compromiso, Grabador, [Responsable De Cobro], Telefonos, [Tipo Cartera], Asesor, [Antiguedad De La Cartera],
    CASE WHEN [Desc_Gestion] = 'Usuario pide volver a llamar' AND [Clase de Gestion] = 'codmaquina' THEN 'No contestan' ELSE [Desc_Gestion] END AS [Nota de la Gestion],
    [Clase de Gestion], [Causal de Mora/Respuesta]
FROM Bloque2_Contactados;

-- Limpieza preventiva de la tabla en memoria
DROP TABLE #FiltroEntidades;
