function ejecutarAccion(url, boton) {
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