WITH 
-- 1. Pre-filtrado y formateo del Discador
CTE_Discador AS (
	SELECT 
		NroCliente_Contrato,
		FechayHora,
		DuracionTotal,
		Categoria,
		Subcategoria,
		Resultado,
		NumeroTelefonico,
		Lote,
		Campana,
		Agente,
		EstadoActualContacto,
		LTRIM(RTRIM(CONCAT(CAST(Agente AS VARCHAR(20)), FORMAT(NumeroTelefonico, '0')))) AS fusion_discador
	FROM [dbo].[Discador]
	WHERE CAST(FechayHora AS DATE) = '{fecha}'
),

-- 2. Pre-filtrado del Lote
CTE_Lote AS (
	SELECT phone_number, Nombre_Lote, codigo_cliente, segmento
	FROM [dbo].[Lote]
	WHERE CAST(Fecha AS DATE) = '{fecha}'
),

-- 3. Pre-filtrado de Causales
CTE_Causales AS (
	SELECT *,
		LTRIM(RTRIM(CONCAT(CAST(NroDeAgente AS VARCHAR(20)), FORMAT(Telefono_utilizado, '0')))) AS fusion_causal
	FROM [dbo].[Causales]
	WHERE CAST(FechayHora AS DATE) = '{fecha}'
	  AND Tipo_de_evento = 'Categorización'
),

-- 4. Centralización de la búsqueda de Asesores
CTE_Asesores_Unicos AS (
	SELECT DISTINCT LTRIM(RTRIM(Grabador)) AS Grabador, Asesor 
	FROM [Vencorp_V2].[gestion].[gestion_adminfo_onedrive]
	WHERE Mes_Gestion IN (SELECT TRY_CAST(value AS INT) FROM STRING_SPLIT('{meses}', ','))
	  AND Asesor IS NOT NULL
	  AND Asesor NOT IN ('Asesor','NULL')
),
CTE_Asesor_Top1 AS (
	SELECT Grabador, Asesor,
	       ROW_NUMBER() OVER (PARTITION BY Grabador ORDER BY Asesor) AS rn
	FROM CTE_Asesores_Unicos
),

-- 5. Unión de los 3 escenarios del negocio
CTE_Universo_Unido AS (
	-- ESCENARIO 1: Contactadas con Cliente Válido
	SELECT 
		_dis.NroCliente_Contrato, _dis.FechayHora, _dis.DuracionTotal, _dis.Categoria, _dis.Subcategoria, _dis.Resultado,
		_causal.Fecha_de_compromiso, _causal.Usuario AS Grabador, _dis.NumeroTelefonico AS Telefonos, _lot.codigo_cliente,
		_lot.segmento, _causal.Comentario, _causal.Causal_de_mora,
		CASE WHEN _dis.Categoria IN (' Contacto',' No contacto') THEN 'TEL' WHEN _dis.Categoria IS NULL OR _dis.Categoria = '' THEN 'codmaquina' ELSE _dis.Categoria END AS [Clase de Gestion]
	FROM CTE_Discador _dis
	LEFT JOIN CTE_Lote _lot ON _dis.NumeroTelefonico = _lot.phone_number
		AND LTRIM(RTRIM(_dis.Lote)) = LTRIM(RTRIM(_lot.Nombre_Lote))
		AND LTRIM(RTRIM(_dis.NroCliente_Contrato)) = LTRIM(RTRIM(_lot.codigo_cliente))
	LEFT JOIN CTE_Causales _causal ON CAST(_dis.FechayHora AS DATE) = CAST(_causal.FechayHora AS DATE)
		AND LTRIM(RTRIM(_dis.Campana)) = LTRIM(RTRIM(_causal.Campana))
		AND LTRIM(RTRIM(_dis.Subcategoria)) = LTRIM(RTRIM(_causal.Subcategoria))
		AND LTRIM(RTRIM(_lot.codigo_cliente)) = LTRIM(RTRIM(_causal.Codigo))
		AND _dis.NumeroTelefonico = _causal.Telefono_utilizado
		AND LTRIM(RTRIM(_dis.NroCliente_Contrato)) = LTRIM(RTRIM(_causal.Codigo))
		AND LTRIM(RTRIM(_dis.Categoria)) = LTRIM(RTRIM(_causal.Categoria))
		AND _dis.Agente = _causal.NroDeAgente
	WHERE _dis.EstadoActualContacto = ' Contactada' AND _dis.NroCliente_Contrato IS NOT NULL AND _dis.NroCliente_Contrato != ''

	UNION ALL

	-- ESCENARIO 2: Vencidas
	SELECT 
		_dis.NroCliente_Contrato, _dis.FechayHora, _dis.DuracionTotal, _dis.Categoria, _dis.Subcategoria, _dis.Resultado,
		NULL AS Fecha_de_compromiso, '' AS Grabador, _dis.NumeroTelefonico AS Telefonos, _lot.codigo_cliente,
		_lot.segmento, '' AS Comentario, '' AS Causal_de_mora,
		CASE WHEN _dis.Categoria IN (' Contacto',' No contacto') THEN 'TEL' WHEN _dis.Categoria IS NULL OR _dis.Categoria = '' THEN 'codmaquina' ELSE _dis.Categoria END AS [Clase de Gestion]
	FROM CTE_Discador _dis
	LEFT JOIN CTE_Lote _lot ON _dis.NumeroTelefonico = _lot.phone_number
		AND _dis.Lote = _lot.Nombre_Lote
		AND LTRIM(RTRIM(_dis.NroCliente_Contrato)) = LTRIM(RTRIM(_lot.codigo_cliente))
	WHERE _dis.EstadoActualContacto = ' Vencida' AND _dis.NroCliente_Contrato IS NOT NULL AND _dis.NroCliente_Contrato != ''

	UNION ALL

	-- ESCENARIO 3: Contactadas sin Cliente (Se cruza por Fusión)
	SELECT 
		_causal.Codigo AS NroCliente_Contrato, _discador.FechayHora, _discador.DuracionTotal, _discador.Categoria, _discador.Subcategoria, _discador.Resultado,
		_causal.Fecha_de_compromiso, _causal.Usuario AS Grabador, _discador.NumeroTelefonico AS Telefonos, _lote.codigo_cliente,
		_lote.segmento, _causal.Comentario, _causal.Causal_de_mora,
		CASE WHEN _discador.Categoria IN (' Contacto',' No contacto') THEN 'TEL' WHEN _discador.Categoria IS NULL OR _discador.Categoria = '' THEN 'codmaquina' ELSE _discador.Categoria END AS [Clase de Gestion]
	FROM CTE_Discador _discador
	LEFT JOIN CTE_Causales _causal ON _discador.fusion_discador = _causal.fusion_causal
		AND LTRIM(RTRIM(_discador.Categoria)) = LTRIM(RTRIM(_causal.Categoria))
		AND LTRIM(RTRIM(_discador.Subcategoria)) = LTRIM(RTRIM(_causal.Subcategoria))
	LEFT JOIN CTE_Lote _lote ON _discador.NumeroTelefonico = _lote.phone_number
		AND LTRIM(RTRIM(_discador.Lote)) = LTRIM(RTRIM(_lote.Nombre_Lote))
		AND LTRIM(RTRIM(_causal.Codigo)) = LTRIM(RTRIM(_lote.codigo_cliente))
	WHERE _discador.EstadoActualContacto = ' Contactada' AND (_discador.NroCliente_Contrato IS NULL OR _discador.NroCliente_Contrato = '')
)

/* ========================================================================= */
/* SELECT FINAL: Formateos y Reglas de Negocio Aplicados una Sola Vez        */
/* ========================================================================= */
SELECT 
	NroCliente_Contrato,
	FORMAT(FechayHora, 'dd/MM/yyyy') AS [Fecha De Gestion],
	ISNULL(CONVERT(VARCHAR(8), FechayHora, 108), '00:00:00') AS [Hora De Gestion],
	FORMAT(DATEADD(SECOND, COALESCE(TRY_CAST(DuracionTotal AS INT), 0), 0), 'HH:mm:ss') AS [Duracion llamada],
	
	CASE
		WHEN Categoria IN (' Contacto',' No contacto') THEN
			CASE 
				WHEN Subcategoria IN (' Usuario contesta the llamada pero no responde', ' Usuario Cuelga La Llamada', ' Acuerdo De Pago', 
									  ' Se Dejo Mensaje Con Tercero', ' No Hubo Acuerdo de pago', ' No Conocen Al Usuario (No Vive / No Trabaja)', 
									  ' No Contestan (Asesor)', ' Usuario indica que ya pago', ' Usuario pide volver a llamar', 
									  ' Tercero No Recibe Mensaje', ' Usuario Solicita Informacion', ' Usuario Fallecido') 
					THEN LTRIM(RTRIM(Subcategoria))
				WHEN Subcategoria = ' Actualizacion de contacto' THEN 'Actualizacion Contacto'
				WHEN Subcategoria = ' Buzon de voz (Asesor)' THEN 'Buzon de voz (Asesor)'
				ELSE LTRIM(RTRIM(Subcategoria))
			END
		WHEN Categoria IS NULL OR Categoria = '' THEN
			CASE
				WHEN Resultado IN (' Conectado en 2do call progress',' No Contesta') THEN 'No contestan'
				WHEN Resultado IN (' Congestión',' Error en Red telefónica',' Formato de número inválido') THEN 'Telefono Fuera de Servicio'
				WHEN Resultado IN (' Detección de Contestador', ' Llamada rechazada') THEN 'Buzon de voz'	
				WHEN Resultado = ' Ocupado' THEN 'Telefono Ocupado'
				ELSE LTRIM(RTRIM(Resultado))
			END
	END AS [Descripcion Codigo De Gestion],
	
	FORMAT(Fecha_de_compromiso, 'dd/MM/yyyy') AS Fecha_Compromiso,
	LTRIM(RTRIM(_uni.Grabador)) AS Grabador,
	'Vencorp' AS [Responsable De Cobro],
	Telefonos,
	
	CASE
		WHEN codigo_cliente IS NULL OR LTRIM(RTRIM(codigo_cliente)) = '' THEN NULL
		WHEN codigo_cliente LIKE 'M%' THEN 'Mobile'
		ELSE 'Home'
	END AS [Tipo Cartera],
	
	ISNULL(_ase.Asesor, '') AS Asesor,
	
	CASE
		WHEN segmento = '2) Rv' THEN 'RV'
		WHEN segmento = '3) Mora 30' THEN 'M30'
		WHEN segmento = '4) Mora 60' THEN 'M60'
		WHEN segmento = '2) 0 a 30' THEN '0-30 dias'
		WHEN segmento = '3) 31 a 60' THEN '31-60 dias'
		WHEN segmento = '4) 61 a 90' THEN '61-90 dias'
		WHEN segmento = '5) 91 a 120' THEN '91-120 dias'
		WHEN segmento = '6) >= 121' THEN '>121 dias'
		ELSE segmento
	END AS [Antiguedad De La Cartera],
	
	LTRIM(RTRIM(REPLACE(REPLACE(REPLACE(REPLACE(Comentario, CHAR(9), ''), CHAR(10), ''), CHAR(13), ''), CHAR(160), ' '))) AS [Nota de la Gestion],
	
	[Clase de Gestion],
	
	CASE
		WHEN Causal_de_mora = 'Mala información en la Venta' THEN 'Mala Informacion en la Venta'
		WHEN Causal_de_mora = 'No Conoce el Numero de su Código de Cliente' THEN 'No Conoce el Numero de su Codigo de Cliente'
		ELSE Causal_de_mora
	END AS [Causal de Mora/Respuesta]

FROM CTE_Universo_Unido _uni
LEFT JOIN CTE_Asesor_Top1 _ase ON _uni.Grabador = _ase.Grabador AND _ase.rn = 1
ORDER BY [NroCliente_Contrato], [Clase de Gestion], [Hora De Gestion];