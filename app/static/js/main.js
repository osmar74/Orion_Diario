// Mapeo de URL a panel
const panelMap = {
    'crear-carpetas': 'panel-crear',
    'verificar-red': 'panel-verificar',
    'distribuir': 'panel-distribuir',
    'discador': 'panel-discador',
    'causales': 'panel-causales',
    'lotes': 'panel-lotes'
};

function insertarEnPanel(panelId, html, exito) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    const body = panel.querySelector('.panel-body');
    const icon = panel.querySelector('.panel-icon');
    if (body) body.innerHTML = html;
    if (icon) icon.textContent = exito ? '✅' : '❌';
    panel.open = true;  // expandir automáticamente
}

function cerrarOtrosDetails(boton) {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    const detailsAbiertos = sidebar.querySelectorAll('details[open]');
    const miDetails = boton.closest('details');
    detailsAbiertos.forEach(d => {
        if (d !== miDetails) {
            d.open = false;
        }
    });
}

function marcarPasoCompletado(paso) {
    const pasoEl = document.querySelector(`.paso[data-paso="${paso}"]`);
    if (pasoEl) {
        const pasos = Array.from(document.querySelectorAll('.paso'));
        const index = pasos.indexOf(pasoEl);
        pasos.forEach((p, i) => {
            p.classList.remove('completado', 'activo');
            if (i < index) p.classList.add('completado');
            else if (i === index) p.classList.add('activo');
        });
    }
}

function actualizarTotalesHeader() {
    const ocrOrion = document.getElementById('totalOrion')?.textContent || '--';
    const ocrAister = document.getElementById('totalAister')?.textContent || '--';
    const elOcrOrion = document.getElementById('ocrOrion');
    const elOcrAister = document.getElementById('ocrAister');
    if (elOcrOrion) elOcrOrion.textContent = ocrOrion;
    if (elOcrAister) elOcrAister.textContent = ocrAister;
}

function ejecutarAccion(url, boton) {
    cerrarOtrosDetails(boton);
    const monitor = document.getElementById('monitor-content');
    if (!monitor) {
        alert('Acción no disponible en esta página. Vuelva a la página principal.');
        return;
    }

    const fechaInput = document.getElementById('fechaInput');
    if (!fechaInput) {
        alert('No se encontró el campo de fecha.');
        return;
    }

    const fecha = fechaInput.value;
    const urlConFecha = url + '?fecha=' + encodeURIComponent(fecha);

    // Determinar a qué panel va dirigida la acción
    let panelId = null;
    for (const [key, value] of Object.entries(panelMap)) {
        if (url.includes(key)) {
            panelId = value;
            break;
        }
    }

    // Mostrar mensaje de progreso dentro del panel destino si existe
    if (panelId) {
        insertarEnPanel(panelId, "<p>⏳ Procesando...</p>", false);
    } else {
        monitor.innerHTML = "<p>⏳ Procesando...</p>";
    }

    const icono = boton.querySelector('.status-icon');
    if (icono) icono.textContent = '🔵';

    fetch(urlConFecha)
        .then(response => response.text())
        .then(html => {
            const exito = html.includes('log-line success') || html.includes('✅');
            if (panelId) {
                insertarEnPanel(panelId, html, exito);
            } else {
                monitor.innerHTML = html;
            }

            // Actualizar icono del botón y barra de progreso
            if (exito) {
                if (icono) icono.textContent = '✅';
                if (url.includes('crear-carpetas')) marcarPasoCompletado('crear');
                else if (url.includes('verificar-red')) marcarPasoCompletado('verificar');
                else if (url.includes('distribuir')) marcarPasoCompletado('distribuir');
                else if (url.includes('discador')) {
                    marcarPasoCompletado('discador');
                    // Actualizar procTotal y cuadre (badges)
                    const matchValidos = html.match(/Válidos:\s*(\d+)/);
                    if (matchValidos) {
                        document.getElementById('procTotal').textContent = matchValidos[1];
                    }
                    const ocrOrion = parseInt(document.getElementById('ocrOrion')?.textContent);
                    const proc = parseInt(matchValidos?.[1]);
                    const cuadreBadge = document.getElementById('cuadreBadge');
                    const cuadreTexto = document.getElementById('cuadreTexto');
                    const cuadreIcono = cuadreBadge?.querySelector('.badge-label');
                    if (!isNaN(ocrOrion) && !isNaN(proc)) {
                        if (ocrOrion === proc) {
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
                else if (url.includes('causales')) marcarPasoCompletado('causales');
                else if (url.includes('lotes')) marcarPasoCompletado('lotes');
            } else if (html.includes('log-line error') || html.includes('❌')) {
                if (icono) icono.textContent = '❌';
            } else if (html.includes('log-line warning') || html.includes('⚠️')) {
                if (icono) icono.textContent = '⚠️';
            } else {
                if (icono) icono.textContent = '✅';
            }
        })
        .catch(error => {
            const errorHtml = `<div class="log-line error">❌ Error de conexión: ${error}</div>`;
            if (panelId) {
                insertarEnPanel(panelId, errorHtml, false);
            } else {
                monitor.innerHTML = errorHtml;
            }
            if (icono) icono.textContent = '❌';
        });
}

function subirOCR() {
    const inputFiles = document.getElementById('ocrFiles');
    const files = inputFiles.files;
    if (files.length === 0) {
        alert('Seleccione al menos una imagen.');
        return;
    }

    const monitor = document.getElementById('monitor-content');
    if (!monitor) {
        alert('Acción no disponible en esta página.');
        return;
    }

    const fechaInput = document.getElementById('fechaInput');
    if (!fechaInput) {
        alert('No se encontró el campo de fecha.');
        return;
    }

    const fecha = fechaInput.value;
    const formData = new FormData();
    formData.append('fecha', fecha);
    for (let i = 0; i < files.length; i++) {
        formData.append('imagenes', files[i]);
    }

    const boton = document.getElementById('btn-ocr');
    cerrarOtrosDetails(boton);
    const icono = boton ? boton.querySelector('.status-icon') : null;
    if (icono) icono.textContent = '🔵';

    insertarEnPanel('panel-ocr', "<p>⏳ Subiendo y procesando imágenes...</p>", false);

    fetch('/accion/ocr-subir', {
        method: 'POST',
        body: formData
    })
    .then(response => response.text())
    .then(html => {
        const exito = html.includes('log-line success') || html.includes('✅');
        insertarEnPanel('panel-ocr', html, exito);

        // Leer totales desde el elemento oculto
        const ocrData = document.getElementById('ocr-data');
        if (ocrData) {
            const orionVal = ocrData.getAttribute('data-orion');
            const aisterVal = ocrData.getAttribute('data-aister');
            if (orionVal && orionVal !== 'None') {
                const spanOrion = document.getElementById('totalOrion');
                if (spanOrion) spanOrion.textContent = orionVal;
            }
            if (aisterVal && aisterVal !== 'None') {
                const spanAister = document.getElementById('totalAister');
                if (spanAister) spanAister.textContent = aisterVal;
            }
        }
        actualizarTotalesHeader();
        if (icono) icono.textContent = '✅';
    })
    .catch(error => {
        const errorHtml = `<div class="log-line error">❌ Error de conexión: ${error}</div>`;
        insertarEnPanel('panel-ocr', errorHtml, false);
        if (icono) icono.textContent = '❌';
    });
}


// Al cargar la página, reflejar totales de sesión en el header
document.addEventListener('DOMContentLoaded', function () {
    actualizarTotalesHeader();
});