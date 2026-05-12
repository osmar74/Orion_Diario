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
    monitor.innerHTML = "<p>⏳ Procesando...</p>";

    const icono = boton.querySelector('.status-icon');
    if (icono) icono.textContent = '🔵';

    fetch(urlConFecha)
        .then(response => response.text())
        .then(html => {
            monitor.innerHTML = html;
            if (html.includes('log-line success') || html.includes('✅')) {
                if (icono) icono.textContent = '✅';
                // Marcar paso según URL
                if (url.includes('crear-carpetas')) marcarPasoCompletado('crear');
                else if (url.includes('verificar-red')) marcarPasoCompletado('verificar');
                else if (url.includes('distribuir')) marcarPasoCompletado('distribuir');
                else if (url.includes('discador')) marcarPasoCompletado('discador');
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
            monitor.innerHTML = `<div class="log-line error">❌ Error de conexión: ${error}</div>`;
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
    monitor.innerHTML = "<p>⏳ Subiendo y procesando imágenes...</p>";

    fetch('/accion/ocr-subir', {
        method: 'POST',
        body: formData
    })
    .then(response => response.text())
    .then(html => {
        monitor.innerHTML = html;
        const matchOrion = html.match(/Orion:\s*(\d+)/);
        const matchAister = html.match(/Aister:\s*(\d+)/);
        if (matchOrion) {
            const spanOrion = document.getElementById('totalOrion');
            if (spanOrion) spanOrion.textContent = matchOrion[1];
        }
        if (matchAister) {
            const spanAister = document.getElementById('totalAister');
            if (spanAister) spanAister.textContent = matchAister[1];
        }
        if (icono) icono.textContent = '✅';
    })
    .catch(error => {
        monitor.innerHTML = `<div class="log-line error">❌ Error de conexión: ${error}</div>`;
        if (icono) icono.textContent = '❌';
    });
}