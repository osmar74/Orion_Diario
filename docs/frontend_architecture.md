## 1. Objetivo

Este documento describe la arquitectura frontend actual del proyecto **Orion Diario**, después del refactor visual y separación de responsabilidades realizado sobre los módulos:

- Gestión Diaria ORION
- Gestión Diaria ASTER
- Consolidar Gestión
- Logs y monitoreo

El objetivo principal del refactor fue separar lógica, presentación y estilos, evitando que un solo archivo JavaScript o HTML concentre todo el comportamiento de la aplicación.

---

## 2. Estructura general frontend

La estructura frontend principal queda organizada así:

```text
app/
├── static/
│   ├── js/
│   │   ├── main.js
│   │   ├── orion.js
│   │   ├── aster.js
│   │   └── consolidado.js
│   │
│   └── css/
│       └── deepblack.css
│
└── templates/
    ├── base.html
    ├── index.html
    ├── logs.html
    │
    └── partials/
        ├── header.html
        ├── monitor.html
        ├── sidebar.html
        │
        ├── aster/
        │   ├── monitor_aster.html
        │   └── sidebar_aster.html
        │
        ├── panels/
        │   ├── panel_ocr.html
        │   ├── panel_crear_carpetas.html
        │   ├── panel_verificar_red.html
        │   ├── panel_distribuir.html
        │   ├── panel_discador.html
        │   ├── panel_causales.html
        │   ├── panel_lotes.html
        │   ├── panel_comparar.html
        │   ├── panel_carga_causales.html
        │   ├── panel_carga_discador.html
        │   ├── panel_carga_lote.html
        │   └── panel_consolidado.html
        │
        └── sidebar/
            ├── timeline.html
            ├── fase_ingreso_carpetas.html
            ├── fase_ocr.html
            ├── fase_distribuir.html
            ├── fase_procesamiento.html
            └── fase_carga.html

3. Orden de carga JavaScript

El orden de carga de scripts en base.html es importante:

main.js
orion.js
aster.js
consolidado.js

Este orden debe respetarse porque orion.js, aster.js y consolidado.js usan helpers globales definidos en main.js.

4. Responsabilidad de cada archivo JS
4.1 main.js

Archivo núcleo del frontend.

Responsabilidades principales:

Helpers generales del frontend.
Manejo de layout.
Selector de módulos.
Cambio visual entre ORION, ASTER y Consolidado.
Cache visual por módulo.
Persistencia de campos importantes.
Restauración de estado al cambiar de módulo.
Exposición de helpers globales para otros archivos JS.

Funciones importantes:

getById
htmlLoading
htmlError
esRespuestaExitosa
getInputValue
fetchTexto
postFormTexto
insertarEnPanel
actualizarTotalesHeader
cerrarOtrosDetails
marcarPasoCompletado
normalizarFechaOrion
seleccionarModulo
guardarVistaModuloActual
restaurarVistaModuloCache

main.js no debe contener lógica operativa específica de ORION, ASTER o Consolidado.

4.2 orion.js

Archivo responsable de la lógica frontend del módulo Gestión Diaria ORION.

Responsabilidades:

Ejecutar acciones ORION.
OCR ORION.
Consolidación manual de totales ORION/Aister.
Procesamiento de Discador, Causales y Lotes.
Inserción/verificación de cargas SQL Server.
Manejo de conexión local/remota ORION.

Funciones principales:

ejecutarAccion
subirOCR
consolidarTotales
probarConexion
seleccionarConexion
actualizarBadgesConexion
insertarDatos
verificarCarga
copiarDistribucionSeleccionada
actualizarEstadoDiscador
actualizarCuadre
4.3 aster.js

Archivo responsable de la lógica frontend del módulo Gestión Diaria ASTER.

Responsabilidades:

OCR ASTER.
Captura de total diario ASTER.
Búsqueda y copia del archivo AfterYYYYMMDD.xlsx.
Normalización de encabezados.
Análisis de entidades Excel.
Consulta SQL ASTER.
Depuración y clasificación.
Conciliación.
Inserción ASTER.
Historial de cargas.
Fase I: usuarios y gestiones ASTER.

Funciones principales:

subirOCRAster
consolidarTotalAster
buscarYCopiarArchivoAster
normalizarEncabezadosAster
analizarEntidadesAster
ejecutarConsultaSqlAster
prepararDepuracionAster
aplicarExclusionesAster
guardarClasificacionAster
conciliarEntidadesAster
ajustarConciliacionAster
probarConexionInsercionAster
prepararInsercionAster
insertarDatosAster
consultarHistorialAster
probarConexionesFaseIAster
prepararFaseIAster
ejecutarFaseIAster
4.4 consolidado.js

Archivo responsable de la lógica frontend del módulo Consolidar Gestión.

Responsabilidades:

Abrir panel de consolidado.
Seleccionar conexión local/remota.
Ejecutar consulta de consolidado.
Aplicar filtros y exportar.

Funciones principales:

abrirConsolidado
seleccionarConexionConsolidado
ejecutarConsultaConsolidado
aplicarFiltroYExportar
5. Partials HTML
5.1 ORION

ORION usa partials ubicados en:

app/templates/partials/panels/
app/templates/partials/sidebar/

Estos partials son incluidos desde:

app/templates/partials/monitor.html
app/templates/partials/sidebar.html
5.2 ASTER

ASTER fue separado del JavaScript y ahora usa:

app/templates/partials/aster/monitor_aster.html
app/templates/partials/aster/sidebar_aster.html

Estos archivos están cargados como templates HTML mediante etiquetas <template>.

El JavaScript no construye el HTML completo manualmente; solo toma el contenido del template y lo inserta dinámicamente cuando el usuario selecciona el módulo ASTER.

6. CSS centralizado

Los estilos se centralizan en:

app/static/css/deepblack.css

Reglas actuales:

No usar style="..." en templates HTML.
Crear clases reutilizables para inputs, botones, filas, notas, paneles y tablas.
Mantener una estética uniforme entre ORION, ASTER y Consolidado.
Si un estilo se repite más de una vez, debe convertirse en clase CSS.

Clases reutilizables importantes:

.ui-form-row
.ui-form-row-compact
.ui-form-row-tight
.ui-input
.ui-input-80
.ui-input-120
.ui-input-date
.ui-select-dark
.ui-label
.ui-label-muted
.ui-mini-label
.ui-panel-description
.ui-btn-primary
.ui-btn-danger
.ui-btn-blue
.ui-btn-blue-sm
.ui-result-block
.ui-warning-block
.ui-sidebar-full
.ui-file-muted
7. Cache visual y persistencia de estado

El cambio de módulo entre ORION, ASTER y Consolidado ya no debe sentirse como empezar desde cero.

main.js mantiene una cache visual por módulo:

vistasModuloCache
moduloActivoActual

También persiste valores importantes en localStorage, por ejemplo:

fechaInput
manualOrion
manualAister
manualTotalAster
asterFechaProceso
asterFechaConsultaSql
asterFaseIFecha
consFecha
consMeses

Esto permite que al cambiar entre módulos se mantenga la fecha y otros campos clave.

8. Sincronización de fecha ASTER

ASTER usa varios campos de fecha en diferentes fases. Para evitar inconsistencias, existe una sincronización centralizada.

Helpers relacionados:

normalizarFechaAster
obtenerFechaProcesoAster
sincronizarFechaAster

Regla:

La fecha ASTER debe mantenerse sincronizada entre sidebar, Fase B, Fase E y Fase I.
9. Auditores frontend

Actualmente existen auditores para validar la arquitectura.

9.1 Auditor de split frontend
python tools\audit_frontend_split.py

Valida:

Archivos JS requeridos.
Orden de scripts.
Que main.js no tenga lógica operativa extraída.
Exports globales mínimos.
9.2 Auditor de estilos inline
python tools\audit_inline_styles.py

Valida:

Que no existan style="..." en templates HTML.
9.3 Auditor de assets frontend
python tools\audit_frontend_assets.py

Valida:

Tamaño de JS/CSS.
Orden de scripts.
Funciones duplicadas.
Exports window.*.
Clases CSS posiblemente sin uso.
Estilos inline.
Referencias críticas por archivo.
10. Validaciones recomendadas antes de cada commit frontend

Antes de hacer commit en cambios visuales o frontend, ejecutar:

python tools\audit_frontend_assets.py
python tools\audit_frontend_split.py
python tools\audit_inline_styles.py

node --check app\static\js\main.js
node --check app\static\js\orion.js
node --check app\static\js\aster.js
node --check app\static\js\consolidado.js

python -m py_compile app\controllers\main_blueprint.py app\__init__.py

python -c "from app import create_app; app=create_app(); print(app.name); print(list(app.blueprints.keys()))"

python tools\health_check.py
11. Reglas para futuros cambios frontend
Regla 1

No agregar lógica operativa nueva en main.js.

Usar:

orion.js        para ORION
aster.js       para ASTER
consolidado.js para Consolidado
Regla 2

No construir HTML largo dentro de JavaScript si puede vivir en un partial.

Preferir:

app/templates/partials/
Regla 3

No usar estilos inline en templates.

Evitar:

style="..."

Usar clases en:

app/static/css/deepblack.css
Regla 4

Si una función debe ser llamada desde un botón HTML con onclick, debe exponerse explícitamente:

window.nombreFuncion = nombreFuncion;
Regla 5

Si un archivo JS nuevo depende de helpers de main.js, main.js debe cargarse primero en base.html.

Regla 6

Toda modificación de módulos debe conservar estado visual y fecha de proceso al cambiar entre ORION, ASTER y Consolidado.

12. Estado actual

Estado del frontend después del refactor:

✅ Frontend dividido por módulo.
✅ Templates sin estilos inline.
✅ CSS centralizado.
✅ ASTER con partials propios.
✅ ORION con partials propios.
✅ Consolidado separado.
✅ Auditores disponibles.
✅ Cache visual por módulo.
✅ Fecha ASTER sincronizada.

"""