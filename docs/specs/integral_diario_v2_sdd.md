# Spec Driven Development

## Integral Diario v2

## 1. Identificación

**Módulo:** Integral Diario v2
**Ruta principal:** `/integral-diario-v2`
**Versión base estable:** `v4.0.0`
**Rama base:** `v4-integral-v2`
**Rama de evolución sugerida:** `v4.1-dev`

El módulo Integral Diario v2 centraliza el flujo diario de procesamiento Integral, reemplazando procesos dispersos por una pantalla web modular, trazable y alineada al formato visual usado por Consolidar Gestión v2, Gestión Diaria Orion v2 y Gestión Diaria ASTER v2.

---

## 2. Objetivo general

Consolidar Integral Diario v2 como un módulo profesional para ejecutar, controlar, validar y auditar el procesamiento diario Integral, permitiendo preparar entorno, validar archivos, ejecutar fases, limpiar información, sincronizar orígenes, cargar tablas, generar archivos oficiales y realizar validaciones finales.

---

## 3. Alcance funcional

El módulo Integral Diario v2 cubre:

1. Carga de contexto.
2. Preparación de entorno.
3. Validación de archivos.
4. Selección y comparación de entidades.
5. Sincronización de origen.
6. Gestión de archivo Integral.
7. Carga de tabla inicial.
8. Limpieza SQL.
9. Eliminación de duplicidad por fases.
10. Generación de archivos oficiales.
11. Carga y validación de información Vencorp.
12. Validación final.
13. Copia y validación de archivos finales.
14. Bitácora visual de ejecución.
15. Control de estados por fase.

---

## 4. Fuera de alcance

No forman parte de este SDD inicial:

* Rediseño de Gestión Diaria Orion v2.
* Rediseño de Gestión Diaria ASTER v2.
* Rediseño de Consolidar Gestión v2.
* Cambio estructural de bases de datos de producción.
* Pruebas destructivas en conexión remota.
* Eliminación de lógica heredada sin diagnóstico previo.
* Reescritura total del módulo sin preservar funcionalidades ya validadas.

---

## 5. Estado actual

El módulo ya cuenta con:

* Pantalla `/integral-diario-v2`.
* Flujo por fases A-J.
* Panel lateral de estado de fases.
* Panel central tipo bitácora dinámica.
* Parciales Jinja para resultados.
* Servicios backend específicos para varias operaciones.
* Conexión local/remota.
* Validación final.
* Carga Vencorp.
* Eliminación de duplicidad.
* Archivos oficiales.
* Integración dentro de `v4-integral-v2`.
* Versión estable publicada como `v4.0.0`.

Pendientes técnicos:

* Auditar que todas las fases tengan contrato de datos uniforme.
* Revisar si existen duplicidades entre `integral_v2` e `integral_diario_v2`.
* Consolidar nombres de servicios y partials.
* Reducir código temporal o heredado.
* Documentar reglas exactas de limpieza y validación.
* Validar que la bitácora central se comporte igual en todas las fases.

---

## 6. Usuario principal

El usuario principal es el operador o administrador encargado de ejecutar el procesamiento diario Integral.

Necesita:

* Cargar contexto del día.
* Seleccionar conexión local o remota.
* Validar archivos antes de procesar.
* Ejecutar fases en orden.
* Ver resultados detallados en el panel central.
* Identificar errores, advertencias y fases correctas.
* Generar archivos oficiales.
* Validar información final antes de cerrar el proceso.
* Evitar duplicidades.
* Mantener trazabilidad de cada fase.

---

## 7. Fases del módulo

| Código | Fase                      | Descripción                                                   |
| ------ | ------------------------- | ------------------------------------------------------------- |
| A      | Contexto                  | Carga configuración, fecha, conexión y rutas base.            |
| B      | Preparar entorno          | Prepara carpetas, rutas y condiciones necesarias.             |
| C      | Validar archivo           | Revisa existencia, formato y estructura del archivo Integral. |
| D      | Entidades                 | Obtiene o selecciona entidades relacionadas al proceso.       |
| E      | Sincronización / limpieza | Ejecuta sincronización, limpieza o preparación de datos.      |
| F      | Procesamiento intermedio  | Aplica reglas de limpieza, duplicidad o generación parcial.   |
| G      | Oficial                   | Genera archivos oficiales o resultados preparados.            |
| H      | Vencorp                   | Ejecuta carga o procesamiento relacionado con Vencorp.        |
| I      | Duplicidad / carga final  | Controla duplicidad y cargas finales asociadas.               |
| J      | Validación final          | Copia, valida y cierra resultados finales.                    |

La denominación exacta de cada fase puede ajustarse según el backend real, pero debe mantenerse la trazabilidad por código de fase.

---

## 8. Estados funcionales

Estados permitidos:

| Estado     | Significado                                                       |
| ---------- | ----------------------------------------------------------------- |
| Pendiente  | La fase aún no fue ejecutada.                                     |
| Ejecutando | La fase está en proceso.                                          |
| Correcto   | La fase terminó correctamente.                                    |
| Verificado | La fase validó datos, pero no necesariamente ejecutó carga final. |
| Generado   | Se generó archivo o salida esperada.                              |
| Cargado    | Se realizó carga de datos.                                        |
| Revisar    | Hay advertencias o diferencias que requieren revisión.            |
| Error      | Ocurrió un error técnico o funcional.                             |
| Bloqueado  | La fase no debe continuar por una condición de control.           |
| Duplicado  | Existen registros previos que impiden continuar automáticamente.  |

Reglas:

* Un resultado exitoso no debe marcarse como Error.
* Una validación positiva debe marcarse como Verificado o Correcto.
* Una generación exitosa debe marcarse como Generado o Correcto.
* Una carga exitosa debe marcarse como Cargado o Correcto.
* Una duplicidad detectada debe bloquear la carga automática.
* Toda fase debe reflejar su estado real en sidebar y panel central.

---

## 9. Requisitos funcionales

### RF-01 — Cargar contexto Integral

El sistema debe cargar contexto según fecha de proceso, conexión y configuración activa.

Criterios:

* Permite seleccionar fecha de proceso.
* Permite seleccionar conexión local o remota.
* Muestra ambiente activo.
* Muestra rutas principales.
* Muestra información de origen y destino.
* Inicializa fases en Pendiente.
* Limpia resultados obsoletos si se recarga contexto.

---

### RF-02 — Preparar entorno

El sistema debe preparar carpetas, rutas y condiciones necesarias para el proceso diario.

Criterios:

* Verifica existencia de carpetas requeridas.
* Crea carpetas cuando corresponda.
* Muestra rutas creadas o existentes.
* Marca Correcto si el entorno queda disponible.
* Marca Revisar o Error si falta acceso o permisos.

---

### RF-03 — Validar archivo Integral

El sistema debe validar la existencia y estructura del archivo Integral.

Criterios:

* Detecta archivo esperado.
* Valida formato.
* Valida columnas mínimas.
* Informa cantidad de registros.
* Informa observaciones si existen.
* No permite avanzar si el archivo es inválido.

---

### RF-04 — Seleccionar entidades

El sistema debe permitir consultar, comparar o seleccionar entidades necesarias para el proceso.

Criterios:

* Muestra entidades detectadas.
* Permite identificar entidades faltantes o nuevas.
* Permite aplicar entidades comparadas si corresponde.
* Registra resultado en panel central.
* Marca Correcto si la selección queda lista.

---

### RF-05 — Sincronizar origen

El sistema debe sincronizar información desde el origen configurado.

Criterios:

* Respeta conexión seleccionada.
* Muestra origen, destino y registros afectados.
* Controla errores de conexión.
* Marca Correcto si la sincronización termina bien.
* Marca Error si falla conexión o consulta.

---

### RF-06 — Gestionar archivo Integral

El sistema debe copiar, preparar o transformar archivos necesarios para el flujo Integral.

Criterios:

* Identifica archivos origen.
* Copia o genera archivos destino.
* Muestra rutas finales.
* Controla archivos inexistentes.
* Marca Generado o Correcto cuando termina.

---

### RF-07 — Cargar tabla inicial

El sistema debe cargar información inicial en tabla de trabajo o tabla destino según configuración.

Criterios:

* Valida archivo antes de cargar.
* Valida conexión.
* Informa registros detectados.
* Informa registros cargados.
* Controla duplicidad si aplica.
* No debe cargar automáticamente si existen registros previos bloqueantes.

---

### RF-08 — Limpieza SQL

El sistema debe ejecutar reglas de limpieza SQL definidas para Integral.

Reglas conocidas:

* En Discador, eliminar nulos sin eliminar registros.
* `Fecha_Compromiso` solo debe existir cuando `Descripcion Codigo De Gestion` sea `Acuerdo de pago`.
* `Tipo Cartera` con valor `Home` debe reemplazarse por vacío.
* `Antigüedad De La Cartera` debe vaciarse completa.
* `Telefono` o `Telefonos` vacío debe eliminar registros.
* `Cliente Nro.` no puede estar vacío; debe reportarse si ocurre.
* Si `Descripcion Codigo De Gestion` es `Acuerdo de Pago` y `Fecha_Compromiso` está vacía, cambiar a `No Hubo Acuerdo`.
* En Manual, aplicar las mismas reglas base.
* Si existen `Telefono` y `Telefono_2`, eliminar `Telefono`, renombrar `Telefono_2`, validar compromiso y guardar archivo oficial.

Criterios:

* Las reglas se ejecutan de forma trazable.
* El resultado muestra registros afectados.
* Las reglas no deben aplicarse silenciosamente.
* Debe mostrarse advertencia si hay datos críticos inconsistentes.

---

### RF-09 — Eliminar duplicidad

El sistema debe ejecutar controles de duplicidad por fase cuando corresponda.

Criterios:

* Detecta registros duplicados.
* Informa registros eliminados o bloqueados.
* No elimina datos sin mostrar resumen.
* Marca Correcto si no hay duplicidad o si fue resuelta.
* Marca Revisar si hay diferencias que requieren decisión manual.

---

### RF-10 — Generar archivo oficial

El sistema debe generar archivos oficiales del proceso Integral.

Criterios:

* Genera archivo en ruta esperada.
* Muestra nombre y ubicación.
* Valida estructura mínima del archivo.
* Marca Generado o Correcto si el archivo queda disponible.
* Marca Error si no puede escribir o validar.

---

### RF-11 — Carga Vencorp

El sistema debe procesar o cargar información Vencorp según las fases definidas.

Criterios:

* Valida conexión.
* Valida tablas o fuentes Vencorp.
* Muestra registros procesados.
* Informa errores SQL.
* Marca Cargado o Correcto si termina correctamente.

---

### RF-12 — Validación final

El sistema debe realizar validación final del flujo Integral.

Criterios:

* Verifica archivos finales.
* Verifica registros procesados.
* Muestra diferencias.
* Muestra observaciones.
* Marca Correcto si el flujo queda completo.
* Marca Revisar si hay diferencias.
* Marca Error si falta información crítica.

---

### RF-13 — Bitácora dinámica

El panel central debe funcionar como bitácora de ejecución.

Criterios:

* Al iniciar, todas las fases aparecen Pendiente.
* Al ejecutar una acción, el resultado se agrega al panel central.
* Debe mostrar tiempos, tablas, mensajes y resúmenes.
* No debe perder resultados relevantes.
* No debe conservar resultados obsoletos al recargar contexto.
* El sidebar resume estado; el panel central muestra detalle.

---

## 10. Requisitos de interfaz

El módulo debe mantener el formato visual Integral:

* Sidebar izquierdo.
* Panel central amplio.
* Tarjetas con bordes redondeados.
* Estados claros por fase.
* Scroll interno en sidebar.
* Scroll interno en panel central.
* Controles superiores visibles.
* Botones compactos.
* Tablas con scroll horizontal si son anchas.
* Mensajes de error visibles y claros.

---

## 11. Requisitos técnicos

### Arquitectura

El módulo debe mantener separación:

* Blueprint para rutas.
* Services para lógica de negocio.
* Partials Jinja para resultados.
* JavaScript para interacción.
* CSS separado para estilos.
* Configuración central para rutas y conexiones.

### Backend

El backend debe:

* Validar parámetros.
* Controlar errores.
* Retornar HTML renderizado o JSON claro.
* No ejecutar acciones destructivas sin validación.
* Mantener trazabilidad de cada fase.
* Separar reglas de negocio de la capa visual.

### Frontend

El frontend debe:

* Ejecutar acciones.
* Actualizar estados.
* Mostrar resultados.
* No duplicar reglas de negocio.
* No construir HTML complejo si puede venir de Jinja.
* Evitar parches acumulados.

---

## 12. Contrato de datos sugerido

Respuesta estándar sugerida:

{
"ok": true,
"fase": "H",
"accion": "integral.vencorp",
"estado": "correcto",
"mensaje": "Carga Vencorp finalizada correctamente.",
"resumen": {
"fecha_proceso": "20260429",
"conexion": "local",
"registros_detectados": 1000,
"registros_procesados": 1000,
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

### RN-01 — Conexión local/remota

* Las pruebas deben ejecutarse en local.
* La conexión remota se considera producción.
* El usuario debe elegir explícitamente la conexión.
* La pantalla debe mostrar LOCAL o REMOTO de forma visible.

### RN-02 — Protección de producción

* No ejecutar pruebas destructivas en remoto.
* Toda carga en remoto debe ser explícita.
* Debe quedar visible el ambiente activo.

### RN-03 — Validación de archivos

* No procesar archivos inexistentes.
* No cargar archivos con columnas críticas faltantes.
* Reportar inconsistencias.
* Mostrar archivo origen y destino.

### RN-04 — Duplicidad

* Validar duplicidad antes de cargas finales.
* Bloquear o advertir si existen registros previos.
* No eliminar datos sin resumen.

### RN-05 — Limpieza de datos

* Toda regla de limpieza debe ser visible y trazable.
* Las reglas no deben ejecutarse de forma oculta.
* Las inconsistencias críticas deben generar observaciones.

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

* Evitar guardar HTML excesivo en localStorage.
* Usar scroll en tablas grandes.
* Evitar congelar navegador con resultados extensos.

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

* `/integral-diario-v2` carga correctamente.
* Sidebar visible.
* Panel central visible.
* Scroll interno funcionando.
* Estados visuales claros.
* Botones visibles.
* Tablas no rompen layout.

### Prueba funcional por fase

| Fase | Resultado esperado                 |
| ---- | ---------------------------------- |
| A    | Contexto cargado                   |
| B    | Entorno preparado                  |
| C    | Archivo validado                   |
| D    | Entidades listas                   |
| E    | Sincronización o limpieza correcta |
| F    | Procesamiento intermedio correcto  |
| G    | Oficial generado                   |
| H    | Vencorp cargado o validado         |
| I    | Duplicidad controlada              |
| J    | Validación final correcta          |

### Prueba de regresión

Después de cualquier cambio en Integral, validar:

* `/orion-diario-v2`
* `/aster-diario-v2`
* `/consolidar-gestion-v2`

---

## 16. Criterios de aceptación final

Integral Diario v2 se considera aceptado cuando:

1. Todas las fases se visualizan.
2. Las fases se pueden ejecutar en orden.
3. El estado de cada fase es coherente.
4. El panel central muestra detalle suficiente.
5. No quedan resultados obsoletos.
6. Las reglas de limpieza se aplican correctamente.
7. Se controla duplicidad.
8. Se generan archivos oficiales.
9. La validación final es clara.
10. `python -m compileall app` termina sin errores.
11. `git status` queda limpio.
12. El cambio queda versionado con commit y tag.

---

## 17. Roadmap técnico

### Etapa 1 — Auditoría funcional

* Revisar fase por fase contra este SDD.
* Confirmar estados reales.
* Confirmar reglas de limpieza.
* Confirmar validación final.

### Etapa 2 — Consolidación técnica

* Revisar duplicidad entre `integral_v2` e `integral_diario_v2`.
* Consolidar servicios.
* Consolidar partials.
* Eliminar código muerto.

### Etapa 3 — Contrato backend/frontend

* Normalizar estructura de respuesta.
* Centralizar estados.
* Reducir lógica visual en JavaScript.

### Etapa 4 — Auditoría final

* Probar flujo completo.
* Validar local/remoto.
* Validar archivos oficiales.
* Crear tag de cierre.

---

## 18. Ramas sugeridas

* v4.1-dev
* auditoria-integral-v2-sdd
* refactor-integral-v2-api-contract
* refactor-integral-v2-services-clean
* auditoria-integral-v2-final

---

## 19. Tags sugeridos

* v4.1-integral-sdd-base
* v4.1-integral-auditoria-funcional-ok
* v4.1-integral-api-contract-ok
* v4.1-integral-services-clean-ok
* v4.1-integral-final-ok

---

## 20. Definición de terminado

Una tarea de Integral Diario v2 se considera terminada cuando:

* Está implementada en rama propia.
* No rompe ORION, ASTER ni Consolidar.
* Tiene prueba manual validada.
* No deja scripts temporales.
* No introduce CSS/JS duplicado.
* Tiene commit descriptivo.
* Si corresponde, tiene tag.
* El flujo completo sigue funcionando.
