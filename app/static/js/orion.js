/* ============================================================
   ORION - LÓGICA DE FRONTEND
   Depende de helpers globales definidos en main.js:
   getById, getInputValue, setValue, setText, htmlLoading,
   htmlError, postFormTexto, fetchTexto, esRespuestaExitosa,
   insertarEnPanel, cerrarOtrosDetails, marcarPasoCompletado,
   actualizarTotalesHeader, normalizarFechaOrion.
   ============================================================ */

function ejecutarAccion(url, boton) {
    cerrarOtrosDetails(boton);

    const monitor = getById("monitor-content");

    if (!monitor) {
        alert("Acción no disponible en esta página.");
        return;
    }

    const fechaRaw = getInputValue("fechaInput");
    const fecha = normalizarFechaOrion(fechaRaw);

    if (!fecha) {
        alert("No se encontró el campo de fecha.");
        return;
    }

    setValue("fechaInput", fecha);

    const panelId = buscarPanelPorUrl(url);
    const separador = url.includes("?") ? "&" : "?";
    const urlConFecha = `${url}${separador}fecha=${encodeURIComponent(fecha)}&_=${Date.now()}`;
    console.log("ORION ejecutando acción:", urlConFecha);

    if (panelId) {
        insertarEnPanel(panelId, htmlLoading("Procesando..."), false);
    } else {
        monitor.innerHTML = htmlLoading("Procesando...");
    }

    const icono = boton?.querySelector(".status-icon");

    if (icono) {
        icono.textContent = "";
    }

    fetch(urlConFecha, {
        method: "GET",
        cache: "no-store",
        headers: {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return response.text();
        })
        .then((html) => {
            const exito = esRespuestaExitosa(html);

            if (panelId) {
                insertarEnPanel(panelId, html, exito);
            } else {
                monitor.innerHTML = html;
            }

            if (icono) {
                icono.textContent = exito ? "✅" : "❌";
            }

            if (exito) {
                const clave = Object.keys(panelMap).find((key) =>
                    url.includes(key)
                );
                const paso = clave ? pasoMap[clave] : null;

                if (paso) {
                    marcarPasoCompletado(paso);
                }
            }

            if (url.includes("discador")) {
                actualizarEstadoDiscador();
                actualizarTotalesHeader();
            }
        })
        .catch((err) => {
            const msg = htmlError(`Error de conexión: ${err}`);

            if (panelId) {
                insertarEnPanel(panelId, msg, false);
            } else {
                monitor.innerHTML = msg;
            }

            if (icono) {
                icono.textContent = "❌";
            }
        });
}


function copiarDistribucionSeleccionada(boton) {
    const fechaRaw = getInputValue("fechaInput");
    const fecha = normalizarFechaOrion(fechaRaw);

    if (!fecha) {
        alert("No se encontró el campo de fecha.");
        return;
    }

    setValue("fechaInput", fecha);

    const checks = Array.from(
        document.querySelectorAll(".chk-distribucion-orion:checked")
    );

    if (!checks.length) {
        alert("Seleccione al menos un archivo para copiar.");
        return;
    }

    const seleccionados = checks.map((check) => ({
        categoria: check.dataset.categoria,
        archivo: check.dataset.archivo,
    }));

    const panelId = "panel-distribuir";

    insertarEnPanel(
        panelId,
        htmlLoading("Copiando archivos seleccionados..."),
        false
    );

    fetch(`/accion/distribuir-seleccionados?_=${Date.now()}`, {
        method: "POST",
        cache: "no-store",
        headers: {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
        body: JSON.stringify({
            fecha,
            seleccionados,
        }),
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return response.text();
        })
        .then((html) => {
            const exito = esRespuestaExitosa(html);

            insertarEnPanel(panelId, html, exito);

            if (boton) {
                boton.classList.remove("btn-procesando", "btn-error", "btn-ok");
                boton.classList.add(exito ? "btn-ok" : "btn-error");
            }
        })
        .catch((error) => {
            insertarEnPanel(
                panelId,
                htmlError(`Error copiando archivos seleccionados: ${error}`),
                false
            );

            if (boton) {
                boton.classList.remove("btn-procesando", "btn-ok");
                boton.classList.add("btn-error");
            }
        });
}


function actualizarEstadoDiscador() {
    const discData = getById("discador-data");

    if (!discData) return;

    const valido = discData.getAttribute("data-valido");
    const cuadre = discData.getAttribute("data-cuadre");

    if (valido) {
        setText("procTotal", valido);
    }

    const cuadreBadge = getById("cuadreBadge");
    const cuadreTexto = getById("cuadreTexto");
    const cuadreIcono = cuadreBadge?.querySelector(".badge-label");

    if (cuadre === "True") {
        if (cuadreBadge) cuadreBadge.className = "badge cuadre ok";
        if (cuadreTexto) cuadreTexto.textContent = "Cuadre correcto";
        if (cuadreIcono) cuadreIcono.textContent = "✅";
    } else {
        if (cuadreBadge) cuadreBadge.className = "badge cuadre error";
        if (cuadreTexto) cuadreTexto.textContent = "No cuadra";
        if (cuadreIcono) cuadreIcono.textContent = "❌";
    }
}


function actualizarCuadre(procTotal) {
    const ocrOrion = parseInt(getById("ocrOrion")?.textContent || "", 10);
    const procNumero = parseInt(procTotal, 10);

    const cuadreBadge = getById("cuadreBadge");
    const cuadreTexto = getById("cuadreTexto");
    const cuadreIcono = cuadreBadge?.querySelector(".badge-label");

    if (Number.isNaN(ocrOrion) || Number.isNaN(procNumero)) {
        return;
    }

    if (ocrOrion === procNumero) {
        if (cuadreBadge) cuadreBadge.className = "badge cuadre ok";
        if (cuadreTexto) cuadreTexto.textContent = "Cuadre correcto";
        if (cuadreIcono) cuadreIcono.textContent = "✅";
    } else {
        if (cuadreBadge) cuadreBadge.className = "badge cuadre error";
        if (cuadreTexto) cuadreTexto.textContent = "No cuadra";
        if (cuadreIcono) cuadreIcono.textContent = "❌";
    }
}


function subirOCR() {
    const inputFiles = getById("ocrFiles");

    if (!inputFiles || !inputFiles.files || inputFiles.files.length === 0) {
        alert("Seleccione al menos una imagen.");
        return;
    }

    const monitor = getById("monitor-content");

    if (!monitor) {
        alert("Acción no disponible en esta página.");
        return;
    }

    const fechaRaw = getInputValue("fechaInput");
    const fecha = normalizarFechaOrion(fechaRaw);

    if (!fecha) {
        alert("No se encontró el campo de fecha.");
        return;
    }

    setValue("fechaInput", fecha);

    const formData = new FormData();
    formData.append("fecha", fecha);

    for (let i = 0; i < inputFiles.files.length; i++) {
        formData.append("imagenes", inputFiles.files[i]);
    }

    const boton = getById("btn-ocr");
    cerrarOtrosDetails(boton);

    const icono = boton?.querySelector(".status-icon");

    if (icono) {
        icono.textContent = "";
    }

    insertarEnPanel(
        "panel-ocr",
        htmlLoading("Subiendo y procesando imágenes..."),
        false,
        "#ocr-result-content"
    );

    postFormTexto("/accion/ocr-subir", formData)
        .then((html) => {
            const exito = esRespuestaExitosa(html);

            insertarEnPanel("panel-ocr", html, exito, "#ocr-result-content");

            const manualDiv = getById("manual-totales");

            if (manualDiv) {
                manualDiv.style.display = "block";
            }

            const ocrData = getById("ocr-data");

            if (ocrData) {
                const orion = ocrData.getAttribute("data-orion");
                const aister = ocrData.getAttribute("data-aister");

                if (orion && orion !== "None") {
                    setValue("manualOrion", orion);
                    setText("totalOrion", orion);
                }

                if (aister && aister !== "None") {
                    setValue("manualAister", aister);
                    setText("totalAister", aister);
                }
            }

            actualizarTotalesHeader();

            if (icono) {
                icono.textContent = exito ? "✅" : "❌";
            }
        })
        .catch((err) => {
            insertarEnPanel(
                "panel-ocr",
                htmlError(`Error: ${err}`),
                false,
                "#ocr-result-content"
            );

            if (icono) {
                icono.textContent = "❌";
            }
        });
}


function consolidarTotales() {
    const orion = getInputValue("manualOrion");
    const aister = getInputValue("manualAister");

    const formData = new FormData();
    formData.append("orion", orion);
    formData.append("aister", aister);

    postFormTexto("/accion/consolidar-totales", formData)
        .then((html) => {
            if (orion) setText("totalOrion", orion);
            if (aister) setText("totalAister", aister);

            actualizarTotalesHeader();

            const panelBody = document.querySelector("#panel-ocr .panel-body");

            if (panelBody) {
                const confirmacion = document.createElement("div");
                confirmacion.innerHTML = html;
                panelBody.appendChild(confirmacion);
            }
        })
        .catch((err) => alert(`Error: ${err}`));
}


function probarConexion(tipo) {
    seleccionarConexion(tipo);
}


function seleccionarConexion(tipo) {
    conexionActiva = tipo === "remoto" ? "remoto" : "local";

    const btnLocal = getById("btnConLocalSidebar");
    const btnRemoto = getById("btnConRemotoSidebar");

    if (btnLocal) {
        btnLocal.classList.toggle("active", conexionActiva === "local");
    }

    if (btnRemoto) {
        btnRemoto.classList.toggle("active", conexionActiva === "remoto");
    }

    const indicador = getById("conexion-actual-indicador");

    if (indicador) {
        indicador.textContent =
            conexionActiva === "local" ? "Local activo" : "Remoto activo";
    }

    fetchTexto(
        `/accion/probar-conexion-activa?conexion=${encodeURIComponent(
            conexionActiva
        )}`
    )
        .then((html) => {
            const exito = esRespuestaExitosa(html);
            actualizarBadgesConexion(exito);
        })
        .catch(() => actualizarBadgesConexion(false));
}


function actualizarBadgesConexion(exito) {
    const clases = exito
        ? "badge-conexion badge-verde"
        : "badge-conexion badge-rojo";

    const tipoConexion =
        conexionActiva === "local" ? "Conexión Local" : "Conexión Remota";

    const texto = `${exito ? "✅" : "❌"} ${tipoConexion}`;

    ["causales", "lote", "discador"].forEach((tipo) => {
        const badge = getById(`badge-${tipo}`);

        if (badge) {
            badge.className = clases;
            badge.textContent = texto;
        }
    });
}


function insertarDatos(tipo, conexion = conexionActiva) {
    const resultadoDiv =
        getById(`resultado-insercion-${tipo}`) ||
        getById("resultado-insercion");

    if (resultadoDiv) {
        resultadoDiv.innerHTML = htmlLoading("Insertando datos...");
    }

    const boton = getById(`btn-carga-${tipo}`);
    const icono = boton?.querySelector(".status-icon");

    if (icono) {
        icono.textContent = "";
    }

    const formData = new FormData();
    formData.append("tipo", tipo);
    formData.append("conexion", conexion);

    postFormTexto("/accion/insertar-datos", formData)
        .then((html) => {
            if (resultadoDiv) {
                resultadoDiv.innerHTML = html;
            }

            const exito = esRespuestaExitosa(html);

            if (icono) {
                icono.textContent = exito ? "✅" : "❌";
            }
        })
        .catch((err) => {
            if (resultadoDiv) {
                resultadoDiv.innerHTML = htmlError(`Error: ${err}`);
            }

            if (icono) {
                icono.textContent = "❌";
            }
        });
}


function verificarCarga(tipo) {
    const panel = getById(`panel-carga-${tipo}`);

    if (!panel) return;

    panel.open = true;

    const body = panel.querySelector(".panel-body");

    if (!body) return;

    body.innerHTML = htmlLoading("Verificando columnas...");

    const formData = new FormData();
    formData.append("tipo", tipo);
    formData.append("conexion", conexionActiva);

    postFormTexto("/accion/verificar-carga", formData)
        .then((html) => {
            body.innerHTML = html;
        })
        .catch((err) => {
            body.innerHTML = htmlError(`Error: ${err}`);
        });
}

/* ---------- EXPOSICIÓN GLOBAL ORION ---------- */
window.ejecutarAccion = ejecutarAccion;
window.copiarDistribucionSeleccionada = copiarDistribucionSeleccionada;
window.actualizarEstadoDiscador = actualizarEstadoDiscador;
window.actualizarCuadre = actualizarCuadre;
window.subirOCR = subirOCR;
window.consolidarTotales = consolidarTotales;
window.probarConexion = probarConexion;
window.seleccionarConexion = seleccionarConexion;
window.actualizarBadgesConexion = actualizarBadgesConexion;
window.insertarDatos = insertarDatos;
window.verificarCarga = verificarCarga;
