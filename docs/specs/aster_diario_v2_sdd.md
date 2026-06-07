# Spec Driven Development

## Gestión Diaria ASTER v2

## 1. Identificación

**Módulo:** Gestión Diaria ASTER v2
**Ruta principal:** `/aster-diario-v2`
**Versión base estable:** `v4.0.0`
**Rama base:** `v4-integral-v2`
**Rama de evolución sugerida:** `v4.1-dev`

El módulo Gestión Diaria ASTER v2 automatiza y controla el flujo diario ASTER mediante una pantalla web por fases, alineada visualmente al formato Integral, Orion y Consolidar Gestión.

---

## 2. Objetivo general

Consolidar Gestión Diaria ASTER v2 como un módulo web profesional, modular y mantenible que permita cargar contexto, validar configuración, ubicar archivos, normalizar datos, depurar entidades, clasificar registros, conciliar información, insertar datos y generar reportes finales del proceso ASTER.

---

## 3. Alcance funcional

El módulo cubre:

1. Carga de contexto ASTER.
2. Prueba de configuración local/remota.
3. Captura del total diario ASTER.
4. Ubicación y copia del archivo ASTER.
5. Normalización del Excel ASTER.
6. Preparación de depuración y validación de entidades.
7. Depuración y clasificación ASTER.
8. Conciliación y validación ASTER.
9. Inserción de datos ASTER.
10. Traer usuarios y gestiones ASTER.
11. Cierre y reporte final.
12. Control visual de estados por fase.

---

## 4. Fuera de alcance

No forman parte de este SDD inicial:

* Rediseño de Gestión Diaria Orion v2.
* Rediseño de Integral Diario v2.
* Rediseño de Consolidar Gestión v2.
* Cambios estructurales en bases de datos de producción.
* Pruebas destructivas en conexión remota.
* Eliminación inmediata de endpoints heredados.
* Reescritura completa del módulo sin diagnóstico previo.

---

## 5. Estado actual

El módulo ya cuenta con:

* Pantalla `/aster-diario-v2`.
* Contexto funcional vía `/api/aster-diario-v2/contexto`.
* Prueba de configuración vía `/api/aster-diario-v2/probar-config`.
* Endpoint central de acciones vía `/api/aster-diario-v2/accion`.
* Layout alineado visualmente al formato Integral.
* Sidebar con Estado ASTER.
* Panel central con Fases Gestión Diaria ASTER.
* Scroll interno en sidebar.
* Scroll interno en panel central.
* Corrección de recarga de contexto para limpiar resultados previos.
* Validación funcional completa de fases A-J.
* Integración en `v4-integral-v2`.
* Versión estable publicada como `v4.0.0`.

Pendientes técnicos:

* Reducir HTML generado desde JavaScript.
* Revisar capas heredadas o fallback dentro de `aster_diario_v2.js`.
* Normalizar contrato backend/frontend.
* Consolidar servicios ASTER.
* Auditar dependencias entre ASTER v1 y ASTER v2.
* Documentar reglas de depuración, clasificación e inserción.

---

## 6. Usuario principal

El usuario principal es el operador o administrador encargado de ejecutar la Gestión Diaria ASTER.

Necesita:

* Cargar contexto del día.
* Elegir conexión local o remota.
* Validar rutas y configuración.
* Ubicar archivo ASTER.
* Ejecutar fases en orden.
* Ver estados claros.
* Validar resultados antes de insertar.
* Evitar duplicidades.
* Generar gestiones o reportes finales.
* Mantener trazabilidad del proceso.

---

## 7. Fases del módulo

| Código | Fase                                          | Descripción                                                  |
| ------ | --------------------------------------------- | ------------------------------------------------------------ |
| A      | Captura del total diario ASTER                | Obtiene el total diario ASTER para control inicial.          |
| B      | Ubicación y copia del archivo ASTER           | Busca el archivo After/ASTER y lo copia a DATA.              |
| C      | Normalización del Excel ASTER                 | Normaliza encabezados y estructura del archivo.              |
| D-E    | Preparar Depuración y Validación de Entidades | Prepara entidades, exclusiones y validaciones.               |
| F      | Depuración y clasificación ASTER              | Aplica reglas de depuración y clasificación.                 |
| G      | Conciliación y validación ASTER               | Compara, valida y concilia datos procesados.                 |
| H      | Inserción de datos ASTER                      | Inserta registros en SQL Server según conexión seleccionada. |
| I      | Traer usuarios y gestiones ASTER              | Obtiene usuarios y gestiones relacionadas.                   |
| J      | Cierre / Reporte final ASTER                  | Genera reporte o cierre final del flujo.                     |

---

## 8. Estados funcionales

Estados permitidos:

| Estado      | Significado                                              |
| ----------- | -------------------------------------------------------- |
| Pendiente   | La fase aún no fue ejecutada.                            |
| Ejecutando  | La fase está en proceso.                                 |
| Correcto    | La fase terminó correctamente.                           |
| Verificado  | La fase validó información correctamente.                |
| Copiado     | El archivo fue copiado correctamente.                    |
| Normalizado | El archivo fue normalizado correctamente.                |
| Clasificado | La clasificación terminó correctamente.                  |
| Conciliado  | La conciliación terminó correctamente.                   |
| Insertado   | Los datos fueron insertados correctamente.               |
| Revisar     | Existen advertencias o diferencias.                      |
| Error       | Ocurrió un error técnico o funcional.                    |
| Bloqueado   | La fase no puede continuar por una condición de control. |
| Duplicado   | Ya existen registros para la fecha o tabla destino.      |

Reglas:

* Un resultado exitoso no debe marcarse como Error.
* Una verificación positiva debe quedar Verificado o Correcto.
* Una copia exitosa debe quedar Copiado o Correcto.
* Una inserción exitosa debe quedar Insertado o Correcto.
* Una fase con diferencias no críticas debe quedar Revisar.
* Una fase con error técnico debe quedar Error.
* Al presionar Cargar contexto, los resultados anteriores no deben conservar estados obsoletos.

---

## 9. Requisitos funcionales

### RF-01 — Cargar contexto ASTER

El sistema debe cargar contexto según fecha de proceso y conexión seleccionada.

Criterios:

* Permite seleccionar fecha de proceso.
* Permite seleccionar conexión local o remota.
* Devuelve configuración activa.
* Muestra rutas principales.
* Muestra información SQL relacionada.
* Inicializa las fases en Pendiente.
* Limpia resultados anteriores al recargar contexto.

---

### RF-02 — Probar configuración

El sistema debe permitir probar rutas y conexiones del entorno ASTER.

Criterios:

* Valida DATA root.
* Valida rutas ASTER.
* Valida conexión SQL local/remota.
* Muestra resultados por elemento.
* Marca Error si falta acceso o conexión.
* No debe ejecutar acciones destructivas.

---

### RF-03 — Captura del total diario ASTER

El sistema debe obtener el total diario ASTER como control inicial.

Criterios:

* Consulta el total correspondiente a la fecha de proceso.
* Muestra la fuente consultada.
* Muestra el total obtenido.
* Marca Correcto si se obtiene el dato.
* Marca Revisar si el total no coincide con valores esperados.
* Marca Error si no puede consultar.

---

### RF-04 — Ubicación y copia del archivo ASTER

El sistema debe buscar el archivo ASTER esperado y copiarlo a la carpeta DATA del día.

Criterios:

* Busca en rutas configuradas.
* Identifica archivo correcto.
* Copia el archivo a destino.
* Muestra ruta origen y ruta destino.
* Marca Copiado o Correcto si finaliza.
* Marca Error si no encuentra el archivo.

---

### RF-05 — Normalización del Excel ASTER

El sistema debe normalizar encabezados y estructura del archivo ASTER.

Criterios:

* Lee el archivo copiado.
* Normaliza encabezados.
* Valida columnas mínimas.
* Genera archivo normalizado si corresponde.
* Muestra cantidad de registros.
* Marca Normalizado o Correcto si termina.

---

### RF-06 — Preparar depuración y validación de entidades

El sistema debe preparar datos para depuración y validación de entidades.

Criterios:

* Detecta entidades.
* Identifica entidades conocidas y nuevas.
* Muestra observaciones.
* Prepara datos para exclusiones o clasificación.
* Marca Correcto si queda listo para continuar.
* Marca Revisar si hay entidades pendientes de decisión.

---

### RF-07 — Depuración y clasificación ASTER

El sistema debe aplicar reglas de depuración y clasificación ASTER.

Criterios:

* Aplica exclusiones.
* Clasifica registros.
* Muestra registros procesados.
* Muestra registros excluidos.
* Muestra registros clasificados.
* Marca Clasificado o Correcto si finaliza.
* Marca Revisar si quedan registros sin clasificación.

---

### RF-08 — Conciliación y validación ASTER

El sistema debe conciliar información procesada contra fuentes o totales esperados.

Criterios:

* Compara totales.
* Compara entidades.
* Detecta diferencias.
* Muestra resumen de conciliación.
* Marca Conciliado o Correcto si todo coincide.
* Marca Revisar si hay diferencias.
* Marca Error si falla la consulta o comparación.

---

### RF-09 — Inserción de datos ASTER

El sistema debe insertar datos ASTER en SQL Server según conexión seleccionada.

Criterios:

* Valida conexión.
* Valida tabla destino.
* Valida duplicidad.
* Inserta registros procesados.
* Muestra registros insertados.
* No inserta automáticamente si detecta duplicidad bloqueante.
* Marca Insertado o Correcto si la carga finaliza.
* Marca Duplicado o Bloqueado si existen registros previos.
* Marca Error si falla la inserción.

---

### RF-10 — Traer usuarios y gestiones ASTER

El sistema debe obtener usuarios y gestiones ASTER para completar el proceso.

Criterios:

* Consulta datos requeridos.
* Valida columnas necesarias.
* Muestra registros obtenidos.
* Genera o prepara gestión si corresponde.
* Marca Correcto si finaliza.
* Marca Revisar si faltan datos.
* Marca Error si falla la consulta.

---

### RF-11 — Cierre / Reporte final ASTER

El sistema debe generar cierre o reporte final del proceso ASTER.

Criterios:

* Resume fases ejecutadas.
* Muestra totales finales.
* Muestra errores o advertencias.
* Genera reporte si corresponde.
* Marca Correcto si el proceso queda cerrado.
* Marca Revisar si hay diferencias pendientes.

---

## 10. Requisitos de interfaz

El módulo debe mantener formato visual Integral:

* Sidebar izquierdo.
* Panel central amplio.
* Tarjetas con bordes redondeados.
* Estado ASTER con scroll interno.
* Panel central con scroll interno.
* Badges de estado claros.
* Círculos de fase visibles.
* Controles superiores compactos.
* Tablas con overflow horizontal cuando sean anchas.
* Sin paneles heredados innecesarios.

Colores sugeridos:

| Estado      | Color             |
| ----------- | ----------------- |
| Pendiente   | Amarillo          |
| Ejecutando  | Azul              |
| Correcto    | Verde             |
| Verificado  | Verde             |
| Copiado     | Verde             |
| Normalizado | Verde             |
| Clasificado | Verde             |
| Conciliado  | Verde             |
| Insertado   | Verde             |
| Revisar     | Naranja           |
| Error       | Rojo              |
| Bloqueado   | Gris o violeta    |
| Duplicado   | Violeta o naranja |

---

## 11. Requisitos técnicos

### Arquitectura

El módulo debe mantener separación progresiva:

* Blueprint para rutas ASTER v2.
* Services para lógica de negocio.
* Templates Jinja para estructura HTML.
* JavaScript para interacción.
* CSS separado para layout y estilo.
* Configuración centralizada para rutas y conexiones.

### Backend

El backend debe:

* Validar parámetros.
* Controlar errores.
* Respetar conexión local/remota.
* Retornar JSON estructurado.
* Retornar HTML renderizado por Jinja cuando corresponda.
* No ejecutar cargas destructivas sin validación previa.
* Separar reglas de negocio de presentación.

### Frontend

El frontend debe:

* Cargar contexto.
* Ejecutar acciones.
* Actualizar estados.
* Mostrar resultados.
* No duplicar reglas de negocio.
* No depender de parches acumulados.
* Evitar construir HTML complejo si puede venir desde backend/Jinja.

---

## 12. Contrato de datos sugerido

Respuesta estándar sugerida:

{
"ok": true,
"fase": "H",
"accion": "aster.insertar",
"estado": "insertado",
"mensaje": "Inserción ASTER finalizada correctamente.",
"resumen": {
"fecha_proceso": "20260429",
"conexion": "local",
"tabla_destino": "dbo.aster_dia_nc",
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
* copiado
* normalizado
* clasificado
* conciliado
* insertado
* revisar
* error
* bloqueado
* duplicado

---

## 13. Reglas de negocio

### RN-01 — Conexión local/remota

* Las pruebas deben ejecutarse en local.
* La conexión remota se considera producción.
* El usuario debe elegir explícitamente la conexión.
* La pantalla debe mostrar LOCAL o REMOTO.

### RN-02 — Protección de producción

* No ejecutar pruebas destructivas en remoto.
* Toda carga remota debe ser explícita.
* Debe quedar visible el ambiente activo.

### RN-03 — Validación de archivo ASTER

* No procesar archivos inexistentes.
* No procesar archivos con columnas críticas faltantes.
* Reportar inconsistencias.
* Mostrar archivo origen y destino.

### RN-04 — Duplicidad

* Validar duplicidad antes de insertar.
* Si existen registros para la fecha, bloquear o advertir.
* No insertar automáticamente si existe duplicidad bloqueante.

### RN-05 — Clasificación

* Las reglas de clasificación deben ser trazables.
* Los registros sin clasificación deben reportarse.
* Las exclusiones deben aparecer en resumen.

### RN-06 — Conciliación

* Toda diferencia de totales debe mostrarse.
* Las diferencias no críticas deben quedar como Revisar.
* Los errores de consulta deben quedar como Error.

---

## 14. Requisitos no funcionales

### Mantenibilidad

* No agregar scripts temporales al versionado.
* No acumular CSS/JS de parche.
* Consolidar cambios en archivos oficiales.
* Mantener nombres claros de servicios y acciones.

### Trazabilidad Git

Cada cambio debe tener:

* Rama específica.
* Commit limpio.
* Tag cuando corresponda.
* `git status` limpio antes de integrar.

### Rendimiento

* Evitar guardar HTML excesivo en `localStorage`.
* Usar scroll horizontal en tablas grandes.
* Evitar congelar navegador con resultados extensos.
* Reducir repintados innecesarios del panel central.

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

* `/aster-diario-v2` carga correctamente.
* Sidebar Estado ASTER visible.
* Panel central visible.
* Scroll interno en sidebar.
* Scroll interno en panel central.
* Badges de estado correctos.
* No aparecen paneles heredados innecesarios.
* La pantalla se mantiene alineada al formato Integral.

### Prueba funcional por fase

| Fase | Resultado esperado   |
| ---- | -------------------- |
| A    | Correcto             |
| B    | Correcto             |
| C    | Correcto             |
| D-E  | Correcto             |
| F    | Correcto             |
| G    | Correcto             |
| H    | Correcto / Insertado |
| I    | Correcto             |
| J    | Correcto             |

### Prueba de regresión

Después de cualquier cambio en ASTER, validar:

* `/orion-diario-v2`
* `/integral-diario-v2`
* `/consolidar-gestion-v2`

---

## 16. Criterios de aceptación final

Gestión Diaria ASTER v2 se considera aceptada cuando:

1. Todas las fases se visualizan correctamente.
2. Todas las fases pueden ejecutarse.
3. Los estados reflejan el resultado real.
4. No existen falsos errores.
5. El contexto se recarga sin conservar resultados obsoletos.
6. La conexión local/remota está controlada.
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
* Confirmar reglas de clasificación.
* Confirmar inserción.
* Confirmar cierre final.

### Etapa 2 — Consolidación frontend

* Identificar HTML generado desde JavaScript.
* Migrar resultados complejos a partials Jinja.
* Reducir uso de `innerHTML`.
* Eliminar capas fallback innecesarias.

### Etapa 3 — Consolidación backend

* Normalizar respuestas JSON.
* Centralizar estados funcionales.
* Consolidar servicios ASTER.
* Separar acciones por fase.

### Etapa 4 — Auditoría final ASTER

* Probar flujo completo.
* Validar local/remoto.
* Validar duplicidad.
* Validar reportes finales.
* Crear tag de cierre.

---

## 18. Ramas sugeridas

* v4.1-dev
* auditoria-aster-v2-sdd
* refactor-aster-v2-api-contract
* refactor-aster-v2-render-backend
* refactor-aster-v2-services-clean
* auditoria-aster-v2-final

---

## 19. Tags sugeridos

* v4.1-aster-sdd-base
* v4.1-aster-auditoria-funcional-ok
* v4.1-aster-api-contract-ok
* v4.1-aster-render-backend-ok
* v4.1-aster-services-clean-ok
* v4.1-aster-final-ok

---

## 20. Definición de terminado

Una tarea de ASTER Diario v2 se considera terminada cuando:

* Está implementada en rama propia.
* No rompe ORION, Integral ni Consolidar.
* Tiene prueba manual validada.
* No deja scripts temporales.
* No introduce CSS/JS duplicado.
* Tiene commit descriptivo.
* Si corresponde, tiene tag.
* El flujo completo sigue funcionando.
