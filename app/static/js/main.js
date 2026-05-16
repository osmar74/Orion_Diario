/* ============================================================
   ORION PROCESOS - LÓGICA DE FRONTEND (main.js)
   ============================================================ */

// ---------- VARIABLES GLOBALES ----------
var conexionActiva = 'local';   // 'local' o 'remoto'

// ---------- MAPEO DE URL A PANELES DEL MONITOR ----------
const panelMap = {
    'crear-carpetas': 'panel-crear',
    'verificar-red': 'panel-verificar',
    'distribuir': 'panel-distribuir',
    'discador': 'panel-discador',
    'causales': 'panel-causales',
    'comparar-lotes': 'panel-comparar',   // ← antes que 'lotes'
    'lotes': 'panel-lotes'
};

const pasoMap = {
    'crear-carpetas': 'crear',
    'verificar-red': 'verificar',
    'distribuir': 'distribuir',
    'discador': 'discador',
    'causales': 'causales',
    'lotes': 'lotes',
    'comparar-lotes': null   // no tiene paso en el timeline
};

// ---------- FUNCIONES GENERALES ----------

/** Normaliza texto para comparación (misma lógica que el backend). */
function normalizar(texto) {
    return texto.toLowerCase().replace(/[^a-z0-9]/g, '');
}

/** Inserta contenido HTML en un panel del monitor, actualiza su icono y lo expande. */
function insertarEnPanel(panelId, html, exito, subSelector = '.panel-body') {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    const container = panel.querySelector(subSelector);
    if (!container) return;
    container.innerHTML = html;
    const icon = panel.querySelector('.panel-icon');
    if (icon) icon.textContent = exito ? '✅' : '❌';
    panel.open = true;
}

/** Actualiza los badges de totales (Orion, Aister) en el subheader. */
function actualizarTotalesHeader() {
    const orion = document.getElementById('totalOrion')?.textContent || '--';
    const aister = document.getElementById('totalAister')?.textContent || '--';
    const elOrion = document.getElementById('ocrOrion');
    const elAister = document.getElementById('ocrAister');
    if (elOrion) elOrion.textContent = orion;
    if (elAister) elAister.textContent = aister;
}

// ---------- SIDEBAR Y TIMELINE ----------

/** Cierra todos los <details> del sidebar excepto el que contiene el botón presionado. */
function cerrarOtrosDetails(boton) {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    const abiertos = sidebar.querySelectorAll('details[open]');
    const miDetails = boton.closest('details');
    abiertos.forEach(d => { if (d !== miDetails) d.open = false; });
}

/** Marca un paso como completado en el timeline vertical. */
function marcarPasoCompletado(paso) {
    console.log('marcarPasoCompletado llamado con paso:', paso);
    const items = document.querySelectorAll('.timeline-item');
    const index = Array.from(items).findIndex(item => item.dataset.paso === paso);
    if (index === -1) return;
    items.forEach((item, i) => {
        const circle = item.querySelector('.timeline-circle');
        item.classList.remove('completado', 'activo');
        circle.classList.remove('completado', 'activo');
        if (i < index) {
            item.classList.add('completado');
            circle.classList.add('completado');
        } else if (i === index) {
            item.classList.add('activo');
            circle.classList.add('activo');
        }
    });
}

/** Alterna la visibilidad del sidebar. */
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('collapsed');
}

// ---------- ACCIONES DE LAS FASES ----------

/** Ejecuta una acción del sidebar (crear carpetas, verificar red, etc.). */
function ejecutarAccion(url, boton) {
    cerrarOtrosDetails(boton);
    const monitor = document.getElementById('monitor-content');
    if (!monitor) { alert('Acción no disponible en esta página.'); return; }
    const fechaInput = document.getElementById('fechaInput');
    if (!fechaInput) { alert('No se encontró el campo de fecha.'); return; }

    const fecha = fechaInput.value;
    const urlConFecha = url + '?fecha=' + encodeURIComponent(fecha);

    // Determinar panel destino
    let panelId = null;
    for (const [key, value] of Object.entries(panelMap)) {
        if (url.includes(key)) { panelId = value; break; }
    }

    // Mostrar progreso
    if (panelId) {
        insertarEnPanel(panelId, '<p>⏳ Procesando...</p>', false);
    } else {
        monitor.innerHTML = '<p>⏳ Procesando...</p>';
    }

    const icono = boton.querySelector('.status-icon');
    if (icono) icono.textContent = '🔵';

    fetch(urlConFecha)
        .then(res => res.text())
        .then(html => {
            const exito = html.includes('log-line success') || html.includes('✅');
            if (panelId) {
                insertarEnPanel(panelId, html, exito);
            } else {
                monitor.innerHTML = html;
            }
            if (icono) icono.textContent = exito ? '✅' : '❌';
            // Marcar paso en timeline
            // Marcar paso en timeline
            if (exito) {
                const clave = Object.keys(panelMap).find(k => url.includes(k));
                const paso = pasoMap[clave];
                if (paso) marcarPasoCompletado(paso);
            }
            // Acciones específicas por URL
            // Acciones específicas por URL
            if (url.includes('discador')) {
                const discData = document.getElementById('discador-data');
                if (discData) {
                    const valido = discData.getAttribute('data-valido');
                    const esperado = discData.getAttribute('data-esperado');
                    const cuadre = discData.getAttribute('data-cuadre');
                    if (valido) {
                        document.getElementById('procTotal').textContent = valido;
                    }
                    // Actualizar badge de cuadre
                    const cuadreBadge = document.getElementById('cuadreBadge');
                    const cuadreTexto = document.getElementById('cuadreTexto');
                    const cuadreIcono = cuadreBadge?.querySelector('.badge-label');
                    if (cuadre === 'True') {
                        if (cuadreBadge) cuadreBadge.className = 'badge cuadre ok';
                        if (cuadreTexto) cuadreTexto.textContent = 'Cuadre correcto';
                        if (cuadreIcono) cuadreIcono.textContent = '✅';
                    } else {
                        if (cuadreBadge) cuadreBadge.className = 'badge cuadre error';
                        if (cuadreTexto) cuadreTexto.textContent = 'No cuadra';
                        if (cuadreIcono) cuadreIcono.textContent = '❌';
                    }
                }
                actualizarTotalesHeader();
            }
        })
        .catch(err => {
            const msg = `<div class="log-line error">❌ Error de conexión: ${err}</div>`;
            if (panelId) {
                insertarEnPanel(panelId, msg, false);
            } else {
                monitor.innerHTML = msg;
            }
            if (icono) icono.textContent = '❌';
        });
}

/** Actualiza el badge de cuadre en el subheader. */
function actualizarCuadre(procTotal) {
    const ocrOrion = parseInt(document.getElementById('ocrOrion')?.textContent);
    const cuadreBadge = document.getElementById('cuadreBadge');
    const cuadreTexto = document.getElementById('cuadreTexto');
    const cuadreIcono = cuadreBadge?.querySelector('.badge-label');
    if (!isNaN(ocrOrion) && !isNaN(procTotal)) {
        if (ocrOrion === procTotal) {
            if (cuadreBadge) cuadreBadge.className = 'badge cuadre ok';
            if (cuadreTexto) cuadreTexto.textContent = 'Cuadre correcto';
            if (cuadreIcono) cuadreIcono.textContent = '✅';
        } else {
            if (cuadreBadge) cuadreBadge.className = 'badge cuadre error';
            if (cuadreTexto) cuadreTexto.textContent = 'No cuadra';
            if (cuadreIcono) cuadreIcono.textContent = '❌';
        }
    }
}

// ---------- OCR ----------
function subirOCR() {
    const inputFiles = document.getElementById('ocrFiles');
    const files = inputFiles.files;
    if (files.length === 0) { alert('Seleccione al menos una imagen.'); return; }
    const monitor = document.getElementById('monitor-content');
    if (!monitor) { alert('Acción no disponible en esta página.'); return; }
    const fechaInput = document.getElementById('fechaInput');
    if (!fechaInput) { alert('No se encontró el campo de fecha.'); return; }

    const fecha = fechaInput.value;
    const formData = new FormData();
    formData.append('fecha', fecha);
    for (let i = 0; i < files.length; i++) {
        formData.append('imagenes', files[i]);
    }

    const boton = document.getElementById('btn-ocr');
    cerrarOtrosDetails(boton);
    const icono = boton?.querySelector('.status-icon');
    if (icono) icono.textContent = '🔵';
    insertarEnPanel('panel-ocr', '<p>⏳ Subiendo y procesando imágenes...</p>', false, '#ocr-result-content');

    fetch('/accion/ocr-subir', { method: 'POST', body: formData })
        .then(res => res.text())
        .then(html => {
            const exito = html.includes('log-line success') || html.includes('✅');
            insertarEnPanel('panel-ocr', html, exito, '#ocr-result-content');
            // Mostrar formulario manual
            const manualDiv = document.getElementById('manual-totales');
            if (manualDiv) manualDiv.style.display = 'block';
            // Rellenar totales desde elemento oculto
            const ocrData = document.getElementById('ocr-data');
            if (ocrData) {
                const orion = ocrData.getAttribute('data-orion');
                const aister = ocrData.getAttribute('data-aister');
                if (orion && orion !== 'None') {
                    const manualOrion = document.getElementById('manualOrion');
                    if (manualOrion) manualOrion.value = orion;
                }
                if (aister && aister !== 'None') {
                    const manualAister = document.getElementById('manualAister');
                    if (manualAister) manualAister.value = aister;
                }
                // Actualizar sidebar y header
                const spanOrion = document.getElementById('totalOrion');
                const spanAister = document.getElementById('totalAister');
                if (orion && orion !== 'None' && spanOrion) spanOrion.textContent = orion;
                if (aister && aister !== 'None' && spanAister) spanAister.textContent = aister;
            }
            actualizarTotalesHeader();
            if (icono) icono.textContent = '✅';
        })
        .catch(err => {
            insertarEnPanel('panel-ocr', `<div class="log-line error">❌ Error: ${err}</div>`, false, '#ocr-result-content');
            if (icono) icono.textContent = '❌';
        });
}

/** Consolida totales ingresados manualmente. */
function consolidarTotales() {
    const orion = document.getElementById('manualOrion').value;
    const aister = document.getElementById('manualAister').value;
    const formData = new FormData();
    formData.append('orion', orion);
    formData.append('aister', aister);

    fetch('/accion/consolidar-totales', { method: 'POST', body: formData })
        .then(res => res.text())
        .then(html => {
            if (orion) document.getElementById('totalOrion').textContent = orion;
            if (aister) document.getElementById('totalAister').textContent = aister;
            actualizarTotalesHeader();
            const panelBody = document.querySelector('#panel-ocr .panel-body');
            if (panelBody) {
                const confirm = document.createElement('div');
                confirm.innerHTML = html;
                panelBody.appendChild(confirm);
            }
        })
        .catch(err => alert('Error: ' + err));
}

// ---------- CONEXIONES Y CARGA A SQL SERVER ----------

/** Prueba conexión local/remoto desde el panel de conexiones (obsoleto, se usa seleccionarConexion). */
function probarConexion(tipo) {
    // Ya no se usa porque la selección se hace desde el sidebar
}

/** Selecciona el tipo de conexión (local/remoto) y actualiza badges. */
function seleccionarConexion(tipo) {
    conexionActiva = tipo;
    document.getElementById('btnConLocalSidebar').classList.toggle('active', tipo === 'local');
    document.getElementById('btnConRemotoSidebar').classList.toggle('active', tipo === 'remoto');

    fetch('/accion/probar-conexion-activa?conexion=' + tipo)
        .then(res => res.text())
        .then(html => {
            const exito = html.includes('success') || html.includes('✅');
            actualizarBadgesConexion(exito);
        })
        .catch(() => actualizarBadgesConexion(false));
}

// Variable global de conexión (ya debe existir)
var conexionActiva = 'local';

function seleccionarConexion(tipo) {
    conexionActiva = tipo;
    // Actualizar estilos de botones
    document.getElementById('btnConLocalSidebar').classList.toggle('active', tipo === 'local');
    document.getElementById('btnConRemotoSidebar').classList.toggle('active', tipo === 'remoto');
    // Actualizar indicador
    const indicador = document.getElementById('conexion-actual-indicador');
    if (indicador) {
        indicador.textContent = tipo === 'local' ? 'Local activo' : 'Remoto activo';
    }
    // Probar conexión y actualizar badges
    fetch('/accion/probar-conexion-activa?conexion=' + tipo)
        .then(res => res.text())
        .then(html => {
            const exito = html.includes('success') || html.includes('✅');
            actualizarBadgesConexion(exito);
        })
        .catch(() => actualizarBadgesConexion(false));
}

function actualizarBadgesConexion(exito) {
    const clases = exito ? 'badge-conexion badge-verde' : 'badge-conexion badge-rojo';
    const texto = (exito ? '✅ ' : '❌ ') + (conexionActiva === 'local' ? 'Local' : 'Remoto');
    ['causales', 'lote', 'discador'].forEach(tipo => {
        const badge = document.getElementById('badge-' + tipo);
        if (badge) {
            badge.className = clases;
            badge.textContent = texto;
        }
    });
}

/** Actualiza los badges de estado de conexión en los paneles de carga. */
function actualizarBadgesConexion(exito) {
    const clases = exito ? 'badge-conexion badge-verde' : 'badge-conexion badge-rojo';
    const tipoConexion = conexionActiva === 'local' ? 'Conexión Local' : 'Conexión Remota';
    const texto = (exito ? '✅ ' : '❌ ') + tipoConexion;
    ['causales', 'lote', 'discador'].forEach(tipo => {
        const badge = document.getElementById('badge-' + tipo);
        if (badge) {
            badge.className = clases;
            badge.textContent = texto;
        }
    });
}


// ---------- RESET ----------

/** Reinicia el proceso (limpia sesión y recarga). */
function resetTodo() {
    if (confirm('¿Está seguro de reiniciar todo el proceso?')) {
        fetch('/reset')
            .then(() => {
                document.querySelectorAll('.paso').forEach(p => p.classList.remove('completado', 'activo'));
                document.querySelectorAll('.panel-icon').forEach(i => i.textContent = '⚪');
                document.querySelectorAll('.panel-body').forEach(b => b.innerHTML = 'Pendiente...');
                document.querySelectorAll('.panel-monitor').forEach(d => d.open = false);
                location.reload();
            })
            .catch(() => location.reload());
    }
}


function insertarDatos(tipo, conexion) {
    const resultadoDiv = document.getElementById('resultado-insercion-' + tipo);
    if (resultadoDiv) {
        resultadoDiv.innerHTML = '<p>⏳ Insertando datos...</p>';
    }

    // Actualizar icono del botón en el sidebar
    const boton = document.getElementById('btn-carga-' + tipo);
    const icono = boton ? boton.querySelector('.status-icon') : null;
    if (icono) icono.textContent = '🔵';

    const formData = new FormData();
    formData.append('tipo', tipo);
    formData.append('conexion', conexion);

    fetch('/accion/insertar-datos', { method: 'POST', body: formData })
        .then(res => res.text())
        .then(html => {
            const div = document.getElementById('resultado-insercion-' + tipo) ||
                document.getElementById('resultado-insercion');
            if (div) div.innerHTML = html;

            const exito = html.includes('log-line success') || html.includes('✅');
            if (icono) icono.textContent = exito ? '✅' : '❌';
        })
        .catch(err => {
            const div = document.getElementById('resultado-insercion-' + tipo) ||
                document.getElementById('resultado-insercion');
            if (div) div.innerHTML = `<div class="log-line error">❌ Error: ${err}</div>`;
            if (icono) icono.textContent = '❌';
        });
}


function verificarCarga(tipo) {
    const panelId = 'panel-carga-' + tipo;
    const panel = document.getElementById(panelId);
    if (!panel) return;
    panel.open = true;
    const body = panel.querySelector('.panel-body');
    if (!body) return;
    body.innerHTML = '<p>⏳ Verificando columnas...</p>';

    const formData = new FormData();
    formData.append('tipo', tipo);
    formData.append('conexion', conexionActiva);  // variable global

    fetch('/accion/verificar-carga', { method: 'POST', body: formData })
        .then(res => res.text())
        .then(html => {
            body.innerHTML = html;
        })
        .catch(err => {
            body.innerHTML = `<div class="log-line error">❌ Error: ${err}</div>`;
        });
}

// Conexión independiente para el panel de consolidado
let conexionConsolidado = 'local';

function abrirConsolidado() {
    const panel = document.getElementById('panel-consolidado');
    if (panel) panel.open = true;
}

function seleccionarConexionConsolidado(tipo) {
    conexionConsolidado = tipo;
    document.getElementById('btnConsLocal').classList.toggle('active', tipo === 'local');
    document.getElementById('btnConsRemoto').classList.toggle('active', tipo === 'remoto');
    const indicador = document.getElementById('cons-conexion-indicador');
    if (indicador) {
        indicador.textContent = tipo === 'local' ? 'Local activo' : 'Remoto activo';
    }
    // Probar conexión y actualizar badge del panel
    fetch('/accion/probar-conexion-consolidado?conexion=' + tipo)
        .then(res => res.text())
        .then(html => {
            const badge = document.getElementById('badge-consolidado');
            const exito = html.includes('success') || html.includes('✅');
            if (badge) {
                badge.className = exito ? 'badge-conexion badge-verde' : 'badge-conexion badge-rojo';
                badge.textContent = (exito ? '✅ ' : '❌ ') + (tipo === 'local' ? 'Local' : 'Remoto');
            }
        })
        .catch(() => {
            const badge = document.getElementById('badge-consolidado');
            if (badge) {
                badge.className = 'badge-conexion badge-rojo';
                badge.textContent = '❌ ' + (tipo === 'local' ? 'Local' : 'Remoto');
            }
        });
}

function ejecutarConsultaConsolidado() {
    const resultado = document.getElementById('cons-resultado');
    resultado.innerHTML = '<p>⏳ Ejecutando consulta...</p>';

    const fecha = document.getElementById('consFecha').value;
    const meses = document.getElementById('consMeses').value;

    const formData = new FormData();
    formData.append('fecha', fecha);
    formData.append('meses', meses);
    formData.append('conexion', conexionConsolidado);

    fetch('/accion/consolidar-consulta', { method: 'POST', body: formData })
        .then(res => res.text())
        .then(html => {
            resultado.innerHTML = html;
        })
        .catch(err => {
            resultado.innerHTML = `<div class="log-line error">❌ Error: ${err}</div>`;
        });
}

function aplicarFiltroYExportar() {
    const resultado = document.getElementById('cons-resultado');
    const checkboxes = resultado.querySelectorAll('input[name="descripcion"]:checked');
    const seleccionados = Array.from(checkboxes).map(cb => cb.value);

    const fecha = document.getElementById('consFecha').value;
    const meses = document.getElementById('consMeses').value;
    const tempId = document.getElementById('cons-temp-id').value;

    const formData = new FormData();
    formData.append('fecha', fecha);
    formData.append('meses', meses);
    formData.append('conexion', conexionConsolidado);
    formData.append('seleccionados', JSON.stringify(seleccionados));
    formData.append('temp_id', tempId);   // <-- nuevo

    resultado.innerHTML = '<p>⏳ Aplicando filtros y generando Excel...</p>';

    fetch('/accion/consolidar-aplicar', { method: 'POST', body: formData })
        .then(res => res.text())
        .then(html => {
            resultado.innerHTML = html;
        })
        .catch(err => {
            resultado.innerHTML = `<div class="log-line error">❌ Error: ${err}</div>`;
        });
}

// ---------- INICIALIZACIÓN ----------
document.addEventListener('DOMContentLoaded', () => {
    actualizarTotalesHeader();
    // Cerrar paneles del monitor
    document.querySelectorAll('.panel-monitor').forEach(d => d.open = false);
    // Mostrar estado inicial de conexión (local no verificado)
    actualizarBadgesConexion(false);
});