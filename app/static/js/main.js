// Mapeo de URL a panel
const panelMap = {
    'crear-carpetas': 'panel-crear',
    'verificar-red': 'panel-verificar',
    'distribuir': 'panel-distribuir',
    'discador': 'panel-discador',
    'causales': 'panel-causales',
    'comparar-lotes': 'panel-comparar',  // <-- nueva línea
    'lotes': 'panel-lotes',
    'causales': 'panel-carga-causales',
    'lote': 'panel-carga-lotes',
    'discador': 'panel-carga-discador',
    'probar-conexion': 'panel-conexiones'
};

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
    // Timeline horizontal antiguo (si aún quedara) -> lo dejamos por si acaso, pero ya no se usa
    // Ahora manipulamos el timeline vertical
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
                else if (url.includes('lotes')) {
                    marcarPasoCompletado('lotes');
                    console.log('Paso lotes completado');  // para depuración, luego se puede quitar
                }
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

    // Insertar progreso en el contenedor de resultados del panel OCR
    insertarEnPanel('panel-ocr', "<p>⏳ Subiendo y procesando imágenes...</p>", false, '#ocr-result-content');

    fetch('/accion/ocr-subir', {
        method: 'POST',
        body: formData
    })
        .then(response => response.text())
        .then(html => {
            const exito = html.includes('log-line success') || html.includes('✅');
            insertarEnPanel('panel-ocr', html, exito, '#ocr-result-content');

            // Mostrar formulario manual
            const manualDiv = document.getElementById('manual-totales');
            if (manualDiv) manualDiv.style.display = 'block';

            // Rellenar campos manuales con los totales detectados (desde el elemento oculto)
            const ocrData = document.getElementById('ocr-data');
            if (ocrData) {
                const orionVal = ocrData.getAttribute('data-orion');
                const aisterVal = ocrData.getAttribute('data-aister');
                if (orionVal && orionVal !== 'None') {
                    const manualOrion = document.getElementById('manualOrion');
                    if (manualOrion) manualOrion.value = orionVal;
                }
                if (aisterVal && aisterVal !== 'None') {
                    const manualAister = document.getElementById('manualAister');
                    if (manualAister) manualAister.value = aisterVal;
                }
            }

            // Actualizar totales en sidebar y header
            const spanOrion = document.getElementById('totalOrion');
            const spanAister = document.getElementById('totalAister');
            if (ocrData) {
                const orionVal = ocrData.getAttribute('data-orion');
                const aisterVal = ocrData.getAttribute('data-aister');
                if (orionVal && orionVal !== 'None' && spanOrion) spanOrion.textContent = orionVal;
                if (aisterVal && aisterVal !== 'None' && spanAister) spanAister.textContent = aisterVal;
            }
            actualizarTotalesHeader();
            if (icono) icono.textContent = '✅';
        })
        .catch(error => {
            const errorHtml = `<div class="log-line error">❌ Error de conexión: ${error}</div>`;
            insertarEnPanel('panel-ocr', errorHtml, false, '#ocr-result-content');
            if (icono) icono.textContent = '❌';
        });
}


function consolidarTotales() {
    const orion = document.getElementById('manualOrion').value;
    const aister = document.getElementById('manualAister').value;
    const formData = new FormData();
    formData.append('orion', orion);
    formData.append('aister', aister);

    fetch('/accion/consolidar-totales', { method: 'POST', body: formData })
        .then(response => response.text())
        .then(html => {
            // Actualizar totales en sidebar y header
            const spanOrion = document.getElementById('totalOrion');
            const spanAister = document.getElementById('totalAister');
            if (orion && spanOrion) spanOrion.textContent = orion;
            if (aister && spanAister) spanAister.textContent = aister;
            actualizarTotalesHeader();
            // Mostrar mensaje en el propio panel OCR
            const panelBody = document.querySelector('#panel-ocr .panel-body');
            if (panelBody) {
                const confirm = document.createElement('div');
                confirm.innerHTML = html;
                panelBody.appendChild(confirm);
            }
        })
        .catch(error => alert('Error: ' + error));
}




function resetTodo() {
    if (confirm('¿Está seguro de reiniciar todo el proceso? Se perderán los totales y estados.')) {
        fetch('/reset')
            .then(() => {
                // Limpiar progreso visual antes de recargar
                document.querySelectorAll('.paso').forEach(p => p.classList.remove('completado', 'activo'));
                document.querySelectorAll('.panel-icon').forEach(i => i.textContent = '⚪');
                document.querySelectorAll('.panel-body').forEach(b => b.innerHTML = 'Pendiente...');
                // Cerrar todos los details del monitor
                document.querySelectorAll('.panel-monitor').forEach(d => d.open = false);
                // Recargar para volver a estado inicial con sesión limpia
                location.reload();
            })
            .catch(() => location.reload());
    }
}

// Cambio de módulo (Orion / Aister / Consolidar)
document.addEventListener('click', function (e) {
    if (e.target.classList.contains('modulo-btn')) {
        document.querySelectorAll('.modulo-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        const modulo = e.target.dataset.modulo;
        if (modulo === 'orion') {
            // Ya estamos en Orion, no hacer nada o refrescar
        } else if (modulo === 'aister') {
            alert('Módulo Aister pendiente de implementar.');
        } else if (modulo === 'consolidar') {
            alert('Consolidación pendiente de implementar.');
        }
    }
});




document.addEventListener('change', function (e) {
    if (e.target.id === 'sqlAuth') {
        const credsDiv = document.getElementById('sqlCreds');
        if (credsDiv) {
            credsDiv.style.display = e.target.value === 'windows' ? 'none' : 'block';
        }
    }
});


function probarConexion(tipo) {
    const servidor = document.getElementById('sqlServidor').value;
    const puerto = document.getElementById('sqlPuerto').value;
    const basedatos = document.getElementById('sqlBasedatos').value;
    const usuario = document.getElementById('sqlUsuario').value;
    const password = document.getElementById('sqlPassword').value;
    const autenticacion = document.getElementById('sqlAuth').value;

    const formData = new FormData();
    formData.append('servidor', servidor);   // <-- siempre el valor original
    formData.append('puerto', puerto);
    formData.append('basedatos', basedatos);
    formData.append('usuario', usuario);
    formData.append('password', password);
    formData.append('autenticacion', autenticacion);

    const panel = document.getElementById('panel-conexiones');
    if (panel) panel.open = true;
    const container = panel ? panel.querySelector('.panel-body') : null;
    if (container) {
        const progressDiv = document.createElement('div');
        progressDiv.innerHTML = '<p>⏳ Probando conexión...</p>';
        container.appendChild(progressDiv);

        fetch('/accion/probar-conexion', { method: 'POST', body: formData })
            .then(response => response.text())
            .then(html => {
                progressDiv.remove();
                const resultDiv = document.createElement('div');
                resultDiv.innerHTML = html;
                container.appendChild(resultDiv);
            })
            .catch(error => {
                progressDiv.remove();
                const errorDiv = document.createElement('div');
                errorDiv.innerHTML = `<div class="log-line error">❌ Error: ${error}</div>`;
                container.appendChild(errorDiv);
            });
    }
}

function probarLectura() {
    const servidor = document.getElementById('sqlServidor').value;
    const puerto = document.getElementById('sqlPuerto').value;
    const basedatos = document.getElementById('sqlBasedatos').value;
    const usuario = document.getElementById('sqlUsuario').value;
    const password = document.getElementById('sqlPassword').value;
    const autenticacion = document.getElementById('sqlAuth').value;

    const formData = new FormData();
    formData.append('servidor', servidor);
    formData.append('puerto', puerto);
    formData.append('basedatos', basedatos);
    formData.append('usuario', usuario);
    formData.append('password', password);
    formData.append('autenticacion', autenticacion);

    const panel = document.getElementById('panel-conexiones');
    if (panel) panel.open = true;
    const container = panel ? panel.querySelector('.panel-body') : null;
    if (container) {
        const progressDiv = document.createElement('div');
        progressDiv.innerHTML = '<p>⏳ Ejecutando consulta...</p>';
        container.appendChild(progressDiv);

        fetch('/accion/probar-lectura', { method: 'POST', body: formData })
            .then(response => response.text())
            .then(html => {
                progressDiv.remove();
                const resultDiv = document.createElement('div');
                resultDiv.innerHTML = html;
                container.appendChild(resultDiv);
            })
            .catch(error => {
                progressDiv.remove();
                const errorDiv = document.createElement('div');
                errorDiv.innerHTML = `<div class="log-line error">❌ Error: ${error}</div>`;
                container.appendChild(errorDiv);
            });
    }
}

// Variable global para la conexión activa en carga
let conexionActiva = 'local';

function setConexion(tipo) {
    conexionActiva = tipo;
    document.getElementById('btnConLocal').classList.toggle('active', tipo === 'local');
    document.getElementById('btnConRemoto').classList.toggle('active', tipo === 'remoto');
}

function verificarCarga(tipo) {
    const formData = new FormData();
    formData.append('tipo', tipo);
    formData.append('conexion', conexionActiva);

    const panel = document.getElementById('panel-carga');
    if (panel) panel.open = true;
    const resultadoDiv = document.getElementById('carga-resultado');
    if (resultadoDiv) {
        resultadoDiv.innerHTML = '<p>⏳ Verificando...</p>';

        fetch('/accion/verificar-carga', { method: 'POST', body: formData })
            .then(response => response.text())
            .then(html => {
                resultadoDiv.innerHTML = html;
            })
            .catch(error => {
                resultadoDiv.innerHTML = `<div class="log-line error">❌ Error: ${error}</div>`;
            });
    }
}


function cargarDatos(tipo) {
    const formData = new FormData();
    formData.append('tipo', tipo);
    formData.append('conexion', conexionActiva);  // variable global ya existente

    const panel = document.getElementById('panel-carga');
    if (panel) panel.open = true;
    const resultadoDiv = document.getElementById('carga-resultado');
    if (resultadoDiv) {
        resultadoDiv.innerHTML = '<p>⏳ Cargando datos...</p>';

        fetch('/accion/cargar-datos', { method: 'POST', body: formData })
            .then(response => response.text())
            .then(html => {
                resultadoDiv.innerHTML = html;
            })
            .catch(error => {
                resultadoDiv.innerHTML = `<div class="log-line error">❌ Error: ${error}</div>`;
            });
    }
}



// Función para seleccionar conexión desde el sidebar y probarla
function seleccionarConexion(tipo) {
    conexionActiva = tipo;
    // Actualizar botones del sidebar
    document.getElementById('btnConLocalSidebar').classList.toggle('active', tipo === 'local');
    document.getElementById('btnConRemotoSidebar').classList.toggle('active', tipo === 'remoto');
    // Probar conexión y actualizar badges en los paneles de carga
    const formData = new FormData();
    formData.append('servidor', tipo === 'local' ? '' : '172.24.80.32');  // podemos usar los datos de config o dejar que el endpoint use sus propios defaults
    formData.append('basedatos', 'Orion');
    // Usamos los datos guardados en config? Mejor confiar en el endpoint que ya tiene la lógica de local/remoto
    // Vamos a llamar a probar-conexion con los parámetros adecuados
    // Pero probar-conexion espera servidor, basedatos, etc. Podemos hacer que seleccionarConexion simplemente actualice la variable y luego intentar una prueba rápida.
    // Para simplificar, llamaremos a probar-conexion usando los mismos valores que el backend usará (podemos obtenerlos de los campos ocultos o fijos).
    // Ya que el backend conoce las configuraciones, podemos hacer un fetch a un nuevo endpoint que solo pruebe la conexión activa.
    // Por ahora, crearemos un endpoint simple '/accion/probar-conexion-activa' que use la variable de sesión o reciba 'conexion'.
    // Alternativa más limpia: que el propio botón de carga verifique la conexión al iniciar.
    // Dado que el usuario quiere badges, hagamos un fetch a un endpoint que devuelva si la conexión está ok.
    fetch('/accion/probar-conexion-activa?conexion=' + tipo)
        .then(res => res.text())
        .then(html => {
            const exito = html.includes('success') || html.includes('✅');
            actualizarBadgesConexion(exito);
        })
        .catch(() => actualizarBadgesConexion(false));
}

// Nuevo endpoint en backend (lo agregaremos abajo)

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

function ejecutarCarga(tipo) {
    const panelId = 'panel-carga-' + tipo;
    const panel = document.getElementById(panelId);
    if (!panel) return;
    panel.open = true;
    const body = panel.querySelector('.panel-body');
    if (!body) return;
    body.innerHTML = '<p>⏳ Ejecutando carga...</p>';

    // Identificar el botón correspondiente en el sidebar
    const boton = document.getElementById('btn-carga-' + tipo);
    const icono = boton ? boton.querySelector('.status-icon') : null;
    if (icono) icono.textContent = '🔵';

    const formData = new FormData();
    formData.append('tipo', tipo);
    formData.append('conexion', conexionActiva);

    fetch('/accion/cargar-datos', { method: 'POST', body: formData })
        .then(response => response.text())
        .then(html => {
            body.innerHTML = html;
            const icon = panel.querySelector('.panel-icon');
            const exito = html.includes('log-line success') || html.includes('✅');
            if (icon) icon.textContent = exito ? '✅' : '❌';
            if (icono) icono.textContent = exito ? '✅' : '❌';  // <-- actualizar botón
        })
        .catch(error => {
            body.innerHTML = `<div class="log-line error">❌ Error: ${error}</div>`;
            const icon = panel.querySelector('.panel-icon');
            if (icon) icon.textContent = '❌';
            if (icono) icono.textContent = '❌';  // <-- actualizar botón en error
        });
}



// Al cargar la página, reflejar totales de sesión en el header
document.addEventListener('DOMContentLoaded', function () {
    actualizarTotalesHeader();
});