function ejecutarAccion(url) {
    const fecha = document.getElementById('fechaInput').value;
    const urlConFecha = url + '?fecha=' + encodeURIComponent(fecha);
    const monitor = document.getElementById('monitor-content');
    monitor.innerHTML = "<p>⏳ Procesando...</p>";

    fetch(urlConFecha)
        .then(response => response.text())
        .then(html => {
            monitor.innerHTML = html;
        })
        .catch(error => {
            monitor.innerHTML = `<div class="log-line error">❌ Error de conexión: ${error}</div>`;
        });
}