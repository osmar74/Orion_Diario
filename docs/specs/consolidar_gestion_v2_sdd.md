# Spec Driven Development

## Consolidar Gestión v2

## 1. Identificación

**Módulo:** Consolidar Gestión v2
**Ruta principal:** `/consolidar-gestion-v2`
**Ruta alternativa heredada:** `/gestion-consolidada`
**Versión base estable:** `v4.0.0`
**Rama base:** `v4-integral-v2`
**Rama de evolución sugerida:** `v4.1-dev`

El módulo Consolidar Gestión v2 permite ejecutar el flujo diario de consolidación de gestión, alineado visualmente al formato Integral, Orion y ASTER, con control de fases, estado persistente, conexión local/remota y validación del proceso.

---

## 2. Objetivo general

Consolidar el módulo **Consolidar Gestión v2** como una pantalla profesional, modular y mantenible para preparar, unir, validar, limpiar, ajustar, generar y cargar información consolidada de gestión, manteniendo trazabilidad por fases y evitando procesos manuales dispersos.

---

## 3. Alcance funcional

El módulo cubre:

1. Selección de fecha de proceso.
2. Selección de mes de gestión.
3. Selección de conexión local/remota.
4. Reinicio de estado.
5. Consulta de resumen SQL inicial.
6. Preparación del proceso.
7. Unión de archivos de gestión.
8. Verificación de calidad.
9. Ajuste de no contestan.
10. Limpieza de nota de gestión.
11. Procesamiento de compromiso.
12. Generación de archivo final.
13. Listado de archivos generados.
14. Carga SQL de gestión consolidada.
15. Control visual de fases y bitácora.

---

## 4. Fuera de alcance

No forman parte de este SDD inicial:

* Rediseño de Orion Diario v2.
* Rediseño de ASTER Diario v2.
* Rediseño de Integral Diario v2.
* Cambios estructurales de base de datos.
* Pruebas destructivas en conexión remota.
* Eliminación inmediata de endpoints heredados que sigan siendo usados.
* Reescritura completa del módulo sin diagnóstico previo.

---

## 5. Estado actual

El módulo ya cuenta con:

* Pantalla `/consolidar-gestion-v2`.
* Ruta alternativa `/gestion-consolidada`.
* Layout alineado al formato Integral.
* Sidebar con estado de fases.
* Panel central con detalle de ejecución.
* Scroll interno en sidebar.
* Scroll interno en panel central.
* Estado persistente backend.
* Botón de reinicio de estado.
* Conexión local/remota sincronizada.
* Fases visuales y funcionales alineadas.
* Integración en `v4-integral-v2`.
* Versión estable publicada como `v4.0.0`.

Pendientes técnicos:

* Auditar contrato de datos de cada acción.
* Reducir duplicidades entre renderizado backend y frontend si existieran.
* Formalizar estados funcionales.
* Revisar persistencia de estado para varios días/fechas.
* Documentar reglas de calidad, limpieza y carga SQL.
* Revisar si `/gestion-consolidada` debe mantenerse como alias o retirarse a futuro.

---

## 6. Usuario principal

El usuario principal es el operador o administrador encargado de consolidar la gestión diaria.

Necesita:

* Seleccionar fecha y mes de gestión.
* Elegir conexión local o remota.
* Ejecutar fases en orden.
* Ver el estado de cada fase.
* Revisar resultados en panel central.
* Validar archivos generados.
* Cargar información consolidada a SQL.
* Evitar duplicidades y errores de carga.
* Reiniciar el estado cuando corresponda.

---

## 7. Fases del módulo

| Código | Fase                 | Descripción                                                    |
| ------ | -------------------- | -------------------------------------------------------------- |
| A      | Resumen SQL inicial  | Consulta tabla resumen inicial SQL para la fecha seleccionada. |
| B      | Preparar proceso     | Prepara carpetas, archivos y condiciones base.                 |
| C      | Unir archivos        | Une archivos de gestión requeridos.                            |
| D      | Verificar calidad    | Revisa calidad, estructura y consistencia de datos.            |
| E      | Ajuste no contestan  | Aplica ajuste porcentual o regla de no contestan.              |
| F      | Limpiar nota gestión | Limpia o normaliza nota de gestión.                            |
| G      | Procesar compromiso  | Procesa compromisos o acuerdos de gestión.                     |
| H      | Archivo final        | Genera archivo final consolidado.                              |
| I      | Archivos generados   | Lista y valida archivos generados.                             |
| J      | Cargar SQL           | Carga información consolidada a SQL Server.                    |

La codificación puede ajustarse según el backend real, pero debe mantenerse trazabilidad clara por fase.

---

## 8. Estados funcionales

Estados permitidos:

| Estado     | Significado                                          |
| ---------- | ---------------------------------------------------- |
| Pendiente  | La fase aún no fue ejecutada.                        |
| Ejecutando | La fase está en proceso.                             |
| Correcto   | La fase terminó correctamente.                       |
| Verificado | La fase validó datos correctamente.                  |
| Generado   | Se generó archivo o salida esperada.                 |
| Cargado    | Se cargó información a SQL.                          |
| Revisar    | Existen advertencias o diferencias.                  |
| Error      | Ocurrió un error técnico o funcional.                |
| Bloqueado  | La fase no puede continuar por condición de control. |
| Duplicado  | Existen registros previos o conflicto de carga.      |

Reglas:

* Un resultado exitoso no debe marcarse como Error.
* Una validación positiva debe marcarse como Verificado o Correcto.
* Una generación correcta debe marcarse como Generado o Correcto.
* Una carga SQL exitosa debe marcarse como Cargado o Correcto.
* Una advertencia no crítica debe quedar como Revisar.
* Una duplicidad debe bloquear o pedir confirmación antes de cargar.

---

## 9. Requisitos funcionales

### RF-01 — Seleccionar fecha y mes de gestión

El sistema debe permitir seleccionar fecha de proceso y mes de gestión.

Criterios:

* La fecha debe estar visible.
* El mes de gestión debe estar visible en la barra superior.
* La selección debe usarse en todas las fases.
* El cambio de fecha o mes no debe conservar estados obsoletos sin control.
* El estado debe corresponder al contexto activo.

---

### RF-02 — Seleccionar conexión local/remota

El sistema debe permitir elegir conexión local o remota.

Criterios:

* LOCAL debe usarse para pruebas.
* REMOTO debe considerarse producción.
* La pantalla debe mostrar el ambiente activo.
* Los botones local/remoto deben sincronizarse con los parámetros enviados.
* No debe ejecutarse carga remota accidentalmente.

---

### RF-03 — Reiniciar estado

El sistema debe permitir reiniciar el estado de fases.

Criterios:

* Reinicia fases a Pendiente.
* Limpia resultados anteriores cuando corresponda.
* Actualiza sidebar y panel central.
* No debe borrar archivos ni datos sin confirmación.
* Debe trabajar contra el estado backend persistido.

---

### RF-04 — Resumen SQL inicial

El sistema debe consultar el resumen inicial SQL para la fecha seleccionada.

Criterios:

* Consulta según fecha y conexión.
* Muestra tabla resumen.
* Muestra totales.
* Marca Correcto si la consulta termina bien.
* Marca Revisar si no hay datos o existen diferencias.
* Marca Error si falla conexión o consulta.

---

### RF-05 — Preparar proceso

El sistema debe preparar carpetas, rutas y archivos necesarios.

Criterios:

* Verifica rutas base.
* Crea carpetas si corresponde.
* Informa archivos requeridos.
* Muestra rutas origen/destino.
* Marca Correcto si el proceso queda preparado.

---

### RF-06 — Unir archivos de gestión

El sistema debe unir archivos requeridos para consolidación.

Criterios:

* Detecta archivos disponibles.
* Valida estructura mínima.
* Une archivos según reglas definidas.
* Muestra registros unidos.
* Muestra archivos omitidos o con error.
* Marca Correcto si la unión termina correctamente.

---

### RF-07 — Verificar calidad

El sistema debe validar calidad de datos.

Criterios:

* Revisa columnas obligatorias.
* Revisa registros nulos críticos.
* Revisa formatos de fecha.
* Revisa campos clave.
* Muestra observaciones.
* Marca Correcto si no hay errores críticos.
* Marca Revisar si hay advertencias.
* Marca Error si faltan columnas críticas.

---

### RF-08 — Ajuste no contestan

El sistema debe aplicar el ajuste definido para no contestan.

Criterios:

* Permite usar porcentaje definido.
* Muestra registros afectados.
* Muestra antes/después cuando corresponda.
* No aplica cambios silenciosamente.
* Marca Correcto si el ajuste termina bien.
* Marca Revisar si hay registros no ajustables.

---

### RF-09 — Limpiar nota de gestión

El sistema debe limpiar o normalizar la nota de gestión.

Criterios:

* Aplica reglas de limpieza definidas.
* Muestra registros afectados.
* Reporta inconsistencias.
* No elimina información crítica sin resumen.
* Marca Correcto si la limpieza termina bien.

---

### RF-10 — Procesar compromiso

El sistema debe procesar compromisos o acuerdos de gestión.

Criterios:

* Identifica registros con compromiso.
* Valida fechas de compromiso.
* Valida campos relacionados.
* Muestra registros procesados.
* Marca Correcto si el procesamiento termina bien.
* Marca Revisar si existen compromisos incompletos.

---

### RF-11 — Generar archivo final

El sistema debe generar archivo final consolidado.

Criterios:

* Genera archivo en ruta esperada.
* Muestra nombre de archivo.
* Muestra ruta final.
* Valida que el archivo exista.
* Marca Generado o Correcto si el archivo queda disponible.
* Marca Error si no puede escribir el archivo.

---

### RF-12 — Listar archivos generados

El sistema debe listar archivos generados para la fecha.

Criterios:

* Muestra archivos disponibles.
* Muestra tamaño, fecha y ruta cuando corresponda.
* Permite verificar existencia.
* Marca Correcto si los archivos requeridos están disponibles.
* Marca Revisar si falta algún archivo esperado.

---

### RF-13 — Cargar SQL

El sistema debe cargar información consolidada a SQL Server.

Criterios:

* Valida conexión.
* Valida tabla destino.
* Valida fecha de proceso.
* Controla duplicidad.
* Inserta registros si corresponde.
* Muestra registros insertados.
* Muestra errores SQL si existen.
* Marca Cargado o Correcto si termina.
* Marca Duplicado, Bloqueado o Revisar si existen registros previos.
* Marca Error si falla la carga.

---

## 10. Requisitos de interfaz

El módulo debe mantener formato visual Integral:

* Sidebar izquierdo.
* Panel central amplio.
* Tarjetas con bordes redondeados.
* Estado de fases con scroll interno.
* Panel central con scroll interno.
* Botones compactos.
* Barra superior con fecha, mes y conexión.
* Tablas con scroll horizontal cuando sean anchas.
* Mensajes de error visibles.
* Resultados detallados en panel central.

Colores sugeridos:

| Estado     | Color             |
| ---------- | ----------------- |
| Pendiente  | Amarillo          |
| Ejecutando | Azul              |
| Correcto   | Verde             |
| Verificado | Verde             |
| Generado   | Verde             |
| Cargado    | Verde             |
| Revisar    | Naranja           |
| Error      | Rojo              |
| Bloqueado  | Gris o violeta    |
| Duplicado  | Violeta o naranja |

---

## 11. Requisitos técnicos

### Arquitectura

El módulo debe mantener separación:

* Blueprint para rutas.
* Services para lógica de negocio.
* Service de estado para persistencia.
* Service UI para datos visuales.
* Renderer service para resultados.
* Templates Jinja para estructura HTML.
* Partials Jinja para paneles y fases.
* JavaScript para interacción.
* CSS separado para layout.

### Backend

El backend debe:

* Validar parámetros.
* Manejar fecha, mes y conexión.
* Persistir estado de fases.
* Retornar HTML renderizado o JSON claro.
* Controlar errores.
* No ejecutar acciones destructivas sin validación.
* Separar reglas de negocio de presentación.

### Frontend

El frontend debe:

* Ejecutar acciones.
* Actualizar estados.
* Manejar colapsables.
* Mantener scroll.
* No duplicar reglas de negocio.
* Evitar parches acumulados.
* No construir HTML complejo si puede venir desde Jinja.

---

## 12. Contrato de datos sugerido

Respuesta estándar sugerida:

{
"ok": true,
"fase": "J",
"accion": "gestion_consolidada.cargar_sql",
"estado": "cargado",
"mensaje": "Carga SQL finalizada correctamente.",
"resumen": {
"fecha_proceso": "20260429",
"mes_gestion": "abril",
"conexion": "local",
"tabla_destino": "dbo.gestion_consolidada",
"registros_detectados": 1000,
"registros_insertados": 1000,
"registros_error": 0
},
"observaciones": [],
"html": "<div>resultado renderizado</div>"
}

Estados backend recomendados:

* pendiente
* ejecutando
* correcto
* verificado
* generado
* cargado
* revisar
* error
* bloqueado
* duplicado

---

## 13. Reglas de negocio

### RN-01 — Fecha y mes de gestión

* Toda fase debe usar la fecha de proceso activa.
* Toda fase que dependa de mes debe usar el mes de gestión activo.
* Si cambia fecha o mes, el estado previo debe reiniciarse o validarse.

### RN-02 — Conexión local/remota

* Las pruebas deben realizarse en local.
* La conexión remota se considera producción.
* El usuario debe elegir explícitamente la conexión.
* La pantalla debe mostrar LOCAL o REMOTO.

### RN-03 — Protección de producción

* No ejecutar pruebas destructivas en remoto.
* Toda carga remota debe ser explícita.
* Debe quedar visible el ambiente activo.

### RN-04 — Duplicidad

* Antes de cargar SQL, validar duplicidad.
* Si existen registros previos, bloquear, advertir o pedir decisión.
* No insertar automáticamente si la duplicidad es bloqueante.

### RN-05 — Calidad de datos

* Columnas críticas faltantes deben producir Error.
* Advertencias no críticas deben producir Revisar.
* Cambios de limpieza deben mostrar resumen.

### RN-06 — Archivos finales

* Todo archivo final generado debe validarse.
* Debe mostrarse ruta final.
* Debe reportarse si el archivo esperado no existe.

---

## 14. Requisitos no funcionales

### Mantenibilidad

* No agregar scripts temporales al versionado.
* No acumular CSS/JS de parche.
* Consolidar cambios en archivos oficiales.
* Mantener nombres claros de servicios y partials.

### Trazabilidad Git

Cada cambio debe tener:

* Rama específica.
* Commit limpio.
* Tag cuando corresponda.
* `git status` limpio antes de integrar.

### Rendimiento

* Evitar cargar tablas excesivas sin scroll.
* Evitar guardar HTML excesivo en localStorage.
* Usar scroll horizontal en tablas grandes.
* Evitar congelamiento del navegador.

### Seguridad

* No subir `.env`.
* No subir `data/`.
* No subir `instance/`.
* No subir `reports/`.
* No subir `diagnosticos/`.
* No exponer credenciales.

---

## 15. Plan de pruebas

### Prueba visual

Validar:

* `/consolidar-gestion-v2` carga correctamente.
* Sidebar visible.
* Panel central visible.
* Scroll interno en sidebar.
* Scroll interno en panel central.
* Fecha, mes y conexión visibles.
* Botón reiniciar visible.
* Colapsables funcionando.
* Tablas no rompen layout.

### Prueba funcional por fase

| Fase | Resultado esperado          |
| ---- | --------------------------- |
| A    | Resumen SQL consultado      |
| B    | Proceso preparado           |
| C    | Archivos unidos             |
| D    | Calidad verificada          |
| E    | Ajuste aplicado             |
| F    | Nota limpiada               |
| G    | Compromiso procesado        |
| H    | Archivo final generado      |
| I    | Archivos generados listados |
| J    | SQL cargado o validado      |

### Prueba de regresión

Después de cualquier cambio en Consolidar, validar:

* `/orion-diario-v2`
* `/aster-diario-v2`
* `/integral-diario-v2`

---

## 16. Criterios de aceptación final

Consolidar Gestión v2 se considera aceptado cuando:

1. Todas las fases se visualizan correctamente.
2. Las fases se pueden ejecutar en orden.
3. Los estados reflejan el resultado real.
4. Fecha y mes se aplican correctamente.
5. Conexión local/remota está controlada.
6. El estado se puede reiniciar.
7. El layout es consistente con Integral.
8. No quedan scripts temporales.
9. `python -m compileall app` termina sin errores.
10. `git status` queda limpio.
11. El cambio queda versionado con commit y tag.

---

## 17. Roadmap técnico

### Etapa 1 — Auditoría funcional

* Revisar fase por fase contra este SDD.
* Confirmar estados reales.
* Confirmar reglas de calidad.
* Confirmar carga SQL.
* Confirmar persistencia de estado.

### Etapa 2 — Contrato backend/frontend

* Normalizar respuestas.
* Centralizar estados.
* Unificar estructura de errores.
* Reducir dependencias visuales en JS.

### Etapa 3 — Consolidación técnica

* Revisar services.
* Revisar renderers.
* Revisar partials.
* Eliminar código muerto.
* Mantener compatibilidad con rutas activas.

### Etapa 4 — Auditoría final Consolidar

* Probar flujo completo.
* Validar local/remoto.
* Validar duplicidad.
* Validar archivos finales.
* Crear tag de cierre.

---

## 18. Ramas sugeridas

* v4.1-dev
* auditoria-consolidar-v2-sdd
* refactor-consolidar-v2-api-contract
* refactor-consolidar-v2-render-backend
* refactor-consolidar-v2-services-clean
* auditoria-consolidar-v2-final

---

## 19. Tags sugeridos

* v4.1-consolidar-sdd-base
* v4.1-consolidar-auditoria-funcional-ok
* v4.1-consolidar-api-contract-ok
* v4.1-consolidar-render-backend-ok
* v4.1-consolidar-services-clean-ok
* v4.1-consolidar-final-ok

---

## 20. Definición de terminado

Una tarea de Consolidar Gestión v2 se considera terminada cuando:

* Está implementada en rama propia.
* No rompe ORION, ASTER ni Integral.
* Tiene prueba manual validada.
* No deja scripts temporales.
* No introduce CSS/JS duplicado.
* Tiene commit descriptivo.
* Si corresponde, tiene tag.
* El flujo completo sigue funcionando.
