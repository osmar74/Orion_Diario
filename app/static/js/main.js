/* ============================================================
   ORION PROCESOS - LÓGICA DE FRONTEND (main.js)
   ============================================================ */

// ---------- VARIABLES GLOBALES ----------
let conexionActiva = 'local';   // 'local' o 'remoto'

// ---------- MAPEO DE URL A PANELES DEL MONITOR ----------
const panelMap = {
    'crear-carpetas':  'panel-crear',
    'verificar-red':   'panel-verificar',
    'distribuir':      'panel-distribuir',
    'discador':        'panel-discador',
    'causales':        'panel-causales',
    'comparar-lotes':  'panel-comparar',   // ← antes que 'lotes'
    'lotes':           'panel-lotes'
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
            if (exito) {
                const paso = Object.keys(panelMap).find(k => url.includes(k));
                if (paso) marcarPasoCompletado(paso);
            }
            // Acciones específicas por URL
            if (url.includes('discador')) {
                const matchValidos = html.match(/Válidos:\s*(\d+)/);
                if (matchValidos) {
                    document.getElementById('procTotal').textContent = matchValidos[1];
                }
                actualizarCuadre(matchValidos ? parseInt(matchValidos[1]) : null);
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

/** Actualiza los badges de estado de conexión en los paneles de carga. */
function actualizarBadgesConexion(exito) {
    const clases = exito ? 'badge-conexion badge-verde' : 'badge-conexion badge-rojo';
    const texto = exito ? '✅ Conectado' : '❌ Desconectado';
    ['causales', 'lote', 'discador'].forEach(tipo => {
        const badge = document.getElementById('badge-' + tipo);
        if (badge) {
            badge.className = clases;
            badge.textContent = texto;
        }
    });
}

/** Ejecuta la carga de un tipo (causales, lote, discador). */
function ejecutarCarga(tipo) {
    const panelId = 'panel-carga-' + tipo;
    const panel = document.getElementById(panelId);
    if (!panel) return;
    panel.open = true;
    const body = panel.querySelector('.panel-body');
    if (!body) return;
    body.innerHTML = '<p>⏳ Ejecutando carga...</p>';

    const boton = document.getElementById('btn-carga-' + tipo);
    const icono = boton?.querySelector('.status-icon');
    if (icono) icono.textContent = '🔵';

    const formData = new FormData();
    formData.append('tipo', tipo);
    formData.append('conexion', conexionActiva);

    fetch('/accion/cargar-datos', { method: 'POST', body: formData })
        .then(res => res.text())
        .then(html => {
            body.innerHTML = html;
            const exito = html.includes('log-line success') || html.includes('✅');
            const icon = panel.querySelector('.panel-icon');
            if (icon) icon.textContent = exito ? '✅' : '❌';
            if (icono) icono.textContent = exito ? '✅' : '❌';
        })
        .catch(err => {
            body.innerHTML = `<div class="log-line error">❌ Error: ${err}</div>`;
            const icon = panel.querySelector('.panel-icon');
            if (icon) icon.textContent = '❌';
            if (icono) icono.textContent = '❌';
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

// ---------- INICIALIZACIÓN ----------
document.addEventListener('DOMContentLoaded', () => {
    actualizarTotalesHeader();
    // Cerrar todos los paneles del monitor al cargar
    document.querySelectorAll('.panel-monitor').forEach(d => d.open = false);
});