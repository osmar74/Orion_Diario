# Spec Driven Development  
## Gestión Diaria Orion v2

## 1. Identificación

**Módulo:** Gestión Diaria Orion v2  
**Ruta principal:** `/orion-diario-v2`  
**Versión base estable:** `v4.0.0`  
**Rama base:** `v4-integral-v2`  
**Rama de evolución sugerida:** `v4.1-dev`  

El módulo Gestión Diaria Orion v2 automatiza y controla el flujo diario de procesamiento Orion mediante fases ejecutables desde una interfaz web alineada visualmente al formato Integral.

---

## 2. Objetivo general

Consolidar Gestión Diaria Orion v2 como un módulo web profesional, modular y mantenible para ejecutar, validar y controlar el flujo diario Orion, incluyendo preparación de carpetas, verificación de red, procesamiento de archivos, comparación de lotes, carga SQL y consolidado final.

---

## 3. Alcance funcional

El módulo cubre:

1. Carga de contexto.
2. Creación de carpetas.
3. Verificación de red.
4. OCR y totales.
5. Distribución de archivos.
6. Procesamiento de Discador.
7. Procesamiento de Causales.
8. Procesamiento de Lotes.
9. Comparación de Lotes.
10. Verificación y carga SQL de Causales.
11. Verificación y carga SQL de Lotes.
12. Verificación y carga SQL de Discador.
13. Consolidado final de Gestión Orion.

---

## 4. Fuera de alcance

No forman parte de este SDD:

- Rediseño de ASTER Diario v2.
- Rediseño de Integral Diario v2.
- Rediseño de Consolidar Gestión v2.
- Eliminación inmediata de endpoints antiguos `/accion/...`.
- Cambios de estructura en base de datos de producción.
- Reescritura completa del backend general.
- Cambios de reglas de negocio no validadas.

---

## 5. Estado actual

El módulo ya cuenta con:

- Pantalla `/orion-diario-v2`.
- Layout alineado visualmente al formato Integral.
- Sidebar con estado de fases.
- Panel central con fases.
- Scroll interno en sidebar y panel central.
- Estados visuales diferenciados.
- Corrección de falsos estados en F4, F1, F2 y F3.
- Validación funcional básica completada.
- Integración en `v4-integral-v2`.
- Versión estable publicada como `v4.0.0`.

Pendientes técnicos:

- Reducir HTML generado desde JavaScript.
- Migrar resultados complejos a partials Jinja.
- Normalizar contrato de datos backend/frontend.
- Reducir dependencia de endpoints heredados.
- Documentar reglas de estados funcionales.

---

## 6. Fases del módulo

| Código | Fase | Descripción |
|---|---|---|
| A | Crear carpetas | Crea o valida estructura diaria Orion. |
| B | Verificar red | Verifica rutas locales/remotas. |
| C | OCR y Totales | Ejecuta o valida OCR y totales. |
| D | Distribuir archivos | Copia o prepara archivos diarios. |
| E1 | Procesar Discador | Procesa archivo Discador. |
| E2 | Procesar Causales | Procesa archivo Causales. |
| E3 | Procesar Lotes | Procesa archivo Lotes. |
| F4 | Comparar Lotes | Compara lotes procesados. |
| F1 | Carga Causales | Verifica e inserta Causales en SQL. |
| F2 | Carga Lotes | Verifica e inserta Lotes en SQL. |
| F3 | Carga Discador | Verifica e inserta Discador en SQL. |
| G | Consolidado Gestión Orion | Genera o consulta consolidado final. |

---

## 7. Estados funcionales

Estados permitidos:

| Estado | Significado |
|---|---|
| Pendiente | La fase aún no fue ejecutada. |
| Ejecutando | La fase está en proceso. |
| Correcto | La fase terminó correctamente. |
| Copiado | La copia o distribución terminó correctamente. |
| Verificado | El archivo o carga fue validado, pero aún no necesariamente insertado. |
| Insertado | Los registros fueron insertados correctamente. |
| Revisar | La fase terminó con advertencias o diferencias. |
| Error | Ocurrió un error técnico o funcional. |
| Duplicado | Ya existen registros para la fecha. |
| Bloqueado | La fase no debe continuar por una condición de control. |

Reglas:

- Un resultado exitoso no debe marcarse como Error.
- Una comparación con “todos los lotes coinciden” debe quedar Correcto.
- Una verificación positiva sin inserción debe quedar Verificado.
- Una inserción correcta debe quedar Insertado.
- Si existen registros previos para la fecha, no debe insertarse automáticamente.

---

## 8. Requisitos funcionales

### RF-01 — Cargar contexto

El sistema debe cargar contexto según fecha de proceso y conexión seleccionada.

Criterios:

- Permite seleccionar fecha.
- Permite seleccionar conexión local/remota.
- Muestra rutas, conexión, base de datos y tablas.
- Inicializa fases correctamente.
- No conserva resultados obsoletos.

### RF-02 — Mostrar estado de fases

El sistema debe mostrar todas las fases en el sidebar.

Criterios:

- Cada fase muestra código, nombre y estado.
- Los colores representan correctamente el estado.
- El sidebar tiene scroll interno.
- No debe deformarse el layout.

### RF-03 — Crear carpetas

Criterios:

- Crea carpetas si no existen.
- Informa si ya existen.
- Marca Correcto si la estructura queda disponible.

### RF-04 — Verificar red

Criterios:

- Valida rutas configuradas.
- Informa rutas disponibles y no disponibles.
- Marca Error o Revisar si faltan rutas críticas.

### RF-05 — OCR y Totales

Criterios:

- Ejecuta o valida OCR y totales.
- Muestra totales detectados.
- Si es opcional, debe indicarse claramente.
- Si se ejecuta bien, marca Correcto.

### RF-06 — Distribuir archivos

Criterios:

- Detecta archivos disponibles.
- Permite copiar archivos seleccionados.
- Informa copiados, omitidos o errores.
- Marca Copiado o Correcto si finaliza bien.

### RF-07 — Procesar Discador, Causales y Lotes

Criterios:

- Cada fase se ejecuta independientemente.
- Muestra registros procesados.
- Muestra archivo origen y archivo generado.
- Marca Correcto si no hay errores críticos.

### RF-08 — Comparar Lotes

Criterios:

- Si todos los lotes coinciden, marca Correcto.
- Si hay diferencias, marca Revisar.
- Si ocurre error técnico, marca Error.

### RF-09 — Cargas SQL F1, F2 y F3

Flujo esperado:

1. Precheck.
2. Verificación de archivo.
3. Validación de duplicidad.
4. Inserción.
5. Validación posterior.

Criterios:

- Si existen registros previos, marca Duplicado o Bloqueado.
- Si el archivo es válido, marca Verificado.
- Si inserta correctamente, marca Insertado.
- Si falla verificación, marca Revisar.
- Si falla inserción, marca Error.

### RF-10 — Consolidado Gestión Orion

Criterios:

- Muestra resumen o KPIs finales.
- Valida información cargada.
- Muestra diferencias si existen.
- Marca Correcto si se genera o consulta correctamente.

---

## 9. Requisitos de interfaz

El módulo debe mantener el formato visual Integral:

- Sidebar izquierdo.
- Panel central principal.
- Tarjetas con bordes redondeados.
- Scroll interno en sidebar.
- Scroll interno en panel central.
- Estados con badges claros.
- Controles superiores compactos.
- Tablas con scroll horizontal si son anchas.

Colores sugeridos:

| Estado | Color |
|---|---|
| Pendiente | Amarillo |
| Ejecutando | Azul |
| Correcto | Verde |
| Verificado | Verde |
| Insertado | Verde |
| Revisar | Naranja |
| Error | Rojo |
| Bloqueado | Violeta o gris |

---

## 10. Requisitos técnicos

### Arquitectura

El módulo debe mantener separación progresiva:

- Blueprint para rutas.
- Services para lógica de negocio.
- Templates Jinja para estructura HTML.
- JavaScript para interacción.
- CSS separado para layout y estilos.

### JavaScript

El JavaScript debe:

- Ejecutar acciones.
- Actualizar estados.
- Manejar errores.
- Evitar construir HTML complejo en cadenas largas.
- Evitar duplicar lógica de negocio.
- Evitar parches acumulados.

### Backend

El backend debe:

- Exponer endpoints claros.
- Retornar JSON estructurado o HTML renderizado por Jinja.
- Validar parámetros obligatorios.
- Controlar errores con respuestas claras.
- Mantener compatibilidad con endpoints actuales mientras no se migren.

---

## 11. Contrato de datos sugerido

Respuesta estándar sugerida para acciones:

```json
{
  "ok": true,
  "fase": "F1",
  "accion": "carga.causales.verificar",
  "estado": "verificado",
  "mensaje": "Archivo validado correctamente.",
  "resumen": {
    "archivo": "causales.xlsx",
    "registros_detectados": 1000,
    "registros_existentes": 0,
    "registros_insertados": null
  },
  "observaciones": [],
  "html": "<div>resultado renderizado</div>"
}