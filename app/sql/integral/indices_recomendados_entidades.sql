-- Integral Diario v2 / Índices recomendados para acelerar Fase B
-- Revisar antes de ejecutar en producción.
-- No se ejecuta automáticamente desde la aplicación.

-- Opción base para filtrar por fecha y devolver entidad:
-- CREATE NONCLUSTERED INDEX IX_comentarios_fecha_entidad
-- ON dbo.comentarios (fecha, entidad);

-- Si la tabla es muy grande y hay consultas frecuentes por fecha:
-- CREATE NONCLUSTERED INDEX IX_comentarios_fecha
-- ON dbo.comentarios (fecha)
-- INCLUDE (entidad);
