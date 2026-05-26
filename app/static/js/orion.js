const ORION_DISTRIBUIR_COPIA_FIELD_NAMES = ["seleccionados", "seleccionados[]", "seleccion", "seleccion[]", "archivos", "archivos[]", "archivo", "archivo[]", "archivos_seleccionados", "archivos_seleccionados[]", "rutas", "rutas[]", "paths", "paths[]"];
/* ============================================================
   ORION - LÓGICA DE FRONTEND
   Depende de helpers globales definidos en main.js:
   getById, getInputValue, setValue, setText, htmlLoading,
   htmlError, postFormTexto, fetchTexto, esRespuestaExitosa,
   insertarEnPanel, cerrarOtrosDetails, marcarPasoCompletado,
   actualizarTotalesHeader, normalizarFechaOrion.
   ============================================================ */






















function normalizarAccionOrion(accion) {
    let valor = String(accion || "").trim();

    valor = valor.replace(/^\/?accion\//i, "");
    valor = valor.replace(/^\/+/, "");

    const mapa = {
        "crear_carpetas": "crear-carpetas",
        "crearCarpetas": "crear-carpetas",
        "crear-carpetas": "crear-carpetas",

        "verificar_red": "verificar-red",
        "verificarRed": "verificar-red",
        "verificar-red": "verificar-red",

        "ocr": "ocr-totales",
        "ocr-subir": "ocr-totales",
        "ocr_totales": "ocr-totales",
        "ocr-totales": "ocr-totales",

        "distribuir": "distribuir",

        "discador": "procesar-discador",
        "procesar_discador": "procesar-discador",
        "procesarDiscador": "procesar-discador",
        "procesar-discador": "procesar-discador",

        "causales": "procesar-causales",
        "procesar_causales": "procesar-causales",
        "procesarCausales": "procesar-causales",
        "procesar-causales": "procesar-causales",

        "lotes": "procesar-lotes",
        "procesar_lotes": "procesar-lotes",
        "procesarLotes": "procesar-lotes",
        "procesar-lotes": "procesar-lotes",

        "comparar_lotes": "comparar-lotes",
        "compararLotes": "comparar-lotes",
        "comparar-lotes": "comparar-lotes",

        "carga-causales": "carga-causales",
        "carga-lotes": "carga-lotes",
        "carga-discador": "carga-discador",
        "consolidado-gestion": "consolidado-gestion",
    };

    return mapa[valor] || valor;
}





function resultadoPanelAccionOrion(accionRaw) {
    const accion = normalizarAccionOrion(accionRaw);

    const paneles = {
        "crear-carpetas": "panel-crear-carpetas",
        "verificar-red": "panel-verificar-red",
        "distribuir": "panel-distribuir",
        "procesar-discador": "panel-discador",
        "procesar-causales": "panel-causales",
        "procesar-lotes": "panel-lotes",
        "comparar-lotes": "panel-comparar",
    };

    return getById(paneles[accion] || "");
}



function wrapperPanelAccionOrion(accionRaw) {
    const accion = normalizarAccionOrion(accionRaw);

    const wrappers = {
        "crear-carpetas": "panel-crear-carpetas-wrapper",
        "verificar-red": "panel-verificar-red-wrapper",
        "distribuir": "panel-distribuir-wrapper",
        "procesar-discador": "panel-discador-wrapper",
        "procesar-causales": "panel-causales-wrapper",
        "procesar-lotes": "panel-lotes-wrapper",
        "comparar-lotes": "panel-comparar-wrapper",
    };

    return getById(wrappers[accion] || "");
}



function fasePorAccionOrion(accionRaw) {
    const accion = normalizarAccionOrion(accionRaw);

    if (ORION_ACTION_TO_PHASE && ORION_ACTION_TO_PHASE[accion]) {
        return ORION_ACTION_TO_PHASE[accion];
    }

    const fases = {
        "probar-conexion": "G",
        "verificar-carga": "G",
        "insertar-datos": "G",
    };

    return fases[accion] || "";
}






function contenedorScrollMonitorOrion() {
    return (
        document.querySelector(".monitor") ||
        document.querySelector("#monitor") ||
        document.querySelector(".monitor-content") ||
        document.scrollingElement ||
        document.documentElement
    );
}

function panelCentralAccionOrion(accionRaw) {
    const wrapper = wrapperPanelAccionOrion(accionRaw);

    if (wrapper) {
        return wrapper;
    }

    const resultado = resultadoPanelAccionOrion(accionRaw);

    if (resultado) {
        const details = resultado.closest("details.panel-monitor");

        if (details) {
            return details;
        }

        const panel = resultado.closest(".panel-monitor");

        if (panel) {
            return panel;
        }
    }

    const accion = normalizarAccionOrion(accionRaw);
    const textoBuscado = {
        "crear-carpetas": "crear carpetas",
        "verificar-red": "verificar red",
    }[accion];

    if (!textoBuscado) {
        return null;
    }

    const candidatos = document.querySelectorAll("details.panel-monitor");

    for (const item of candidatos) {
        const summary = item.querySelector(":scope > summary");
        const texto = String(summary?.textContent || "").toLowerCase();

        if (texto.includes(textoBuscado)) {
            return item;
        }
    }

    return null;
}

function resaltarPanelCentralOrion(panel) {
    if (!panel) {
        return;
    }

    panel.classList.remove("orion-panel-focus-flash");

    // Forzar reflow para reiniciar animación
    void panel.offsetWidth;

    panel.classList.add("orion-panel-focus-flash");

    setTimeout(() => {
        panel.classList.remove("orion-panel-focus-flash");
    }, 1800);
}


function abrirPanelAccionOrion(accionRaw) {
    const panel = panelCentralAccionOrion(accionRaw);

    if (!panel) {
        console.warn("No se encontró panel central para acción ORION:", accionRaw);
        return;
    }

    if (panel.tagName && panel.tagName.toLowerCase() === "details") {
        panel.open = true;
    }

    resaltarPanelCentralOrion(panel);

    setTimeout(() => {
        const contenedor = contenedorScrollMonitorOrion();

        try {
            panel.scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
        } catch {
            // Fallback para navegadores viejos
        }

        if (
            contenedor &&
            contenedor !== document.scrollingElement &&
            contenedor !== document.documentElement
        ) {
            const top =
                panel.getBoundingClientRect().top -
                contenedor.getBoundingClientRect().top +
                contenedor.scrollTop -
                16;

            contenedor.scrollTo({
                top,
                behavior: "smooth",
            });
        }
    }, 120);
}



function botonesRelacionadosAccionOrion(accionRaw, boton = null) {
    const accion = normalizarAccionOrion(accionRaw);

    const ids = {
        "crear-carpetas": [
            "btn-crear-carpetas",
            "btn-panel-crear-carpetas",
        ],
        "verificar-red": [
            "btn-verificar-red",
            "btn-panel-verificar-red",
        ],
    };

    const encontrados = [];

    if (boton) {
        encontrados.push(boton);
    }

    (ids[accion] || []).forEach((id) => {
        const item = getById(id);

        if (item) {
            encontrados.push(item);
        }
    });

    document.querySelectorAll("button").forEach((item) => {
        const onclick = item.getAttribute("onclick") || "";

        if (
            onclick.includes(accion) ||
            onclick.includes(accion.replace("-", "_"))
        ) {
            encontrados.push(item);
        }
    });

    return [...new Set(encontrados)].filter(Boolean);
}

function actualizarBotonesAccionOrion(accionRaw, exito, boton = null) {
    const botones = botonesRelacionadosAccionOrion(accionRaw, boton);

    botones.forEach((item) => {
        if (typeof actualizarIconoBoton === "function") {
            actualizarIconoBoton(item, exito);
            return;
        }

        let icono = item.querySelector(".status-icon");

        if (!icono) {
            icono = document.createElement("span");
            icono.className = "status-icon";
            item.appendChild(icono);
        }

        icono.textContent = exito ? "✅" : "❌";
    });
}

function prepararYEjecutarAccionOrion(accionRaw, boton = null) {
    const accion = normalizarAccionOrion(accionRaw);

    abrirPanelAccionOrion(accion);

    const fechaPanel = getInputValue("fechaInputPanelCrear");
    const fechaPrincipal = getInputValue("fechaInput");
    const fecha = fechaPanel || fechaPrincipal;

    if (fecha && typeof sincronizarFechaOrionPanel === "function") {
        sincronizarFechaOrionPanel(fecha);
    }

    return ejecutarAccion(accion, boton);
}


function ejecutarAccion(accionRaw, boton = null) {
    const accion = normalizarAccionOrion(accionRaw);
    const accionEndpoint = accion === "ocr-totales" ? "ocr-subir" : accion;

    abrirPanelAccionOrion(accionEndpoint);

    const panel = resultadoPanelAccionOrion(accionEndpoint);
    const fase = fasePorAccionOrion(accion);

    const fechaRaw =
        getInputValue("fechaInputPanelCrear") ||
        getInputValue("fechaInput");

    const fecha = normalizarFechaOrion(fechaRaw);

    if (!fecha) {
        alert("Ingrese una fecha válida antes de ejecutar la acción.");
        actualizarBotonesAccionOrion(accionEndpoint, false, boton);
        return;
    }

    if (typeof sincronizarFechaOrionPanel === "function") {
        sincronizarFechaOrionPanel(fecha);
    } else {
        setValue("fechaInput", fecha);
    }

    actualizarEstadoOperacionOrion(
        accion,
        fase,
        "running",
        "Ejecutando acción..."
    );

    if (panel) {
        panel.innerHTML = htmlLoading(`Ejecutando ${accionEndpoint}...`);
    }

    const url = `/accion/${encodeURIComponent(accionEndpoint)}?fecha=${encodeURIComponent(fecha)}&_=${Date.now()}`;

    return fetchTexto(url, {
        cache: "no-store",
        headers: {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    })
        .then((html) => {
            const exito = esRespuestaExitosa(html);

            if (panel) {
                panel.innerHTML = html;
            }

            actualizarBotonesAccionOrion(accionEndpoint, exito, boton);

            actualizarEstadoOperacionOrion(
                accion,
                fase,
                exito ? "done" : "error",
                exito ? "Completado" : "Error"
            );

            if (typeof programarActualizacionEstadoOrionDesdePaneles === "function") {
                programarActualizacionEstadoOrionDesdePaneles();
            }

            return html;
        })
        .catch((err) => {
            if (panel) {
                panel.innerHTML = htmlError(`Error: ${err}`);
            }

            actualizarBotonesAccionOrion(accionEndpoint, false, boton);

            actualizarEstadoOperacionOrion(
                accion,
                fase,
                "error",
                String(err)
            );

            return "";
        });
}
















const ORION_DISTRIBUIR_COPIA_ENDPOINTS = ["/accion/distribuir-seleccionados"];

































function copiarDistribucionSeleccionada(boton = null) {
    const panel = obtenerPanelResultadoDistribucionOrion();
    const seleccionados = obtenerSeleccionadosDistribucionOrion();

    if (!seleccionados.length) {
        alert("Seleccione al menos un archivo para copiar.");
        return;
    }

    const fechaRaw =
        getInputValue("fechaInputPanelCrear") ||
        getInputValue("fechaInput");

    const fecha = normalizarFechaOrion(fechaRaw);

    if (!fecha) {
        alert("No se encontró una fecha válida para copiar archivos.");
        return;
    }

    if (typeof sincronizarFechaOrionPanel === "function") {
        sincronizarFechaOrionPanel(fecha);
    } else {
        setValue("fechaInput", fecha);
    }

    if (typeof actualizarEstadoFaseOrion === "function") {
        actualizarEstadoFaseOrion("D", "running", "Copiando archivos seleccionados...");
    }

    if (panel) {
        panel.innerHTML = htmlLoading("Copiando archivos seleccionados...");
    }

    return fetch(`/accion/distribuir-seleccionados?_=${Date.now()}`, {
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
            const exito = actualizarEstadoDistribucionOrionDesdeHtml(html);

            if (panel) {
                panel.innerHTML = html;
            }

            if (boton && typeof actualizarIconoBoton === "function") {
                actualizarIconoBoton(boton, exito);
            }

            return html;
        })
        .catch((error) => {
            const mensaje = `Error copiando archivos seleccionados: ${error}`;

            if (panel) {
                panel.innerHTML = htmlError(mensaje);
            }

            if (boton && typeof actualizarIconoBoton === "function") {
                actualizarIconoBoton(boton, false);
            }

            if (typeof actualizarEstadoFaseOrion === "function") {
                actualizarEstadoFaseOrion("D", "error", String(error));
            }

            return "";
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












function setTotalesMonitorOrion(orion, aister) {
    const valorOrion = String(orion ?? "").trim();
    const valorAister = String(aister ?? "").trim();

    if (valorOrion !== "") {
        localStorage.setItem("orionDiario.ui.totalOrion", valorOrion);
        setValue("manualOrion", valorOrion);
        setText("totalOrion", valorOrion);
        setText("ocrOrion", valorOrion);
    }

    if (valorAister !== "") {
        localStorage.setItem("orionDiario.ui.totalAister", valorAister);
        setValue("manualAister", valorAister);
        setText("totalAister", valorAister);
        setText("ocrAister", valorAister);
    }

    actualizarTotalesHeader();
}



function actualizarNombreArchivosOcr() {
    const inputFiles = getById("ocrFiles");
    const resumen = getById("ocrFilesResumen");

    if (!resumen) {
        return;
    }

    if (!inputFiles || !inputFiles.files || inputFiles.files.length === 0) {
        resumen.textContent = "Ningún archivo seleccionado";
        return;
    }

    if (inputFiles.files.length === 1) {
        resumen.textContent = inputFiles.files[0].name;
        return;
    }

    resumen.textContent = `${inputFiles.files.length} archivos seleccionados`;
}

function setModoOcrOrion(modo) {
    const panel = getById("panel-ocr");
    const seccionOcr = getById("orion-ocr-mode");
    const seccionManual = getById("orion-manual-mode");
    const btnOcr = getById("btnModoOcrOrion");
    const btnManual = getById("btnModoManualOrion");
    const tituloManual = getById("manual-totales-titulo");

    if (panel) {
        panel.open = true;
    }

    const modoOcr = modo === "ocr";

    if (seccionOcr) {
        seccionOcr.classList.toggle("active", modoOcr);
    }

    if (seccionManual) {
        seccionManual.classList.toggle("active", !modoOcr);
    }

    if (btnOcr) {
        btnOcr.classList.toggle("active", modoOcr);
    }

    if (btnManual) {
        btnManual.classList.toggle("active", !modoOcr);
    }

    if (tituloManual) {
        tituloManual.textContent = modoOcr
            ? "📝 Corregir o confirmar totales reconocidos antes de consolidar:"
            : "📝 Ingresar totales manualmente:";
    }
}

function mostrarModoOcrOrion() {
    setModoOcrOrion("ocr");
}

function mostrarModoManualOrion() {
    setModoOcrOrion("manual");
}



function activarOProcesarOcrOrion() {
    mostrarModoOcrOrion();
}

function subirOCR() {
    mostrarModoOcrOrion();

    const inputFiles = getById("ocrFiles");
    const resultado = getById("ocr-result-content");

    if (!resultado) {
        alert("No se encontró el panel de resultado OCR.");
        return;
    }

    if (!inputFiles || !inputFiles.files || inputFiles.files.length === 0) {
        alert("Seleccione al menos una imagen.");
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
    const icono = boton?.querySelector(".status-icon");

    if (icono) {
        icono.textContent = "";
    }

    resultado.innerHTML = htmlLoading("Subiendo y procesando imágenes...");

    postFormTexto("/accion/ocr-subir", formData)
        .then((html) => {
            const exito = esRespuestaExitosa(html);

            resultado.innerHTML = html;

            const ocrData = getById("ocr-data");

            if (ocrData) {
                const orion = ocrData.getAttribute("data-orion");
                const aister = ocrData.getAttribute("data-aister");

                if (orion && orion !== "None") {
                    setValue("manualOrion", orion);
                }

                if (aister && aister !== "None") {
                    setValue("manualAister", aister);
                }

                setTotalesMonitorOrion(orion, aister);
            }

            if (icono) {
                icono.textContent = exito ? "✅" : "❌";
            }
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error: ${err}`);

            if (icono) {
                icono.textContent = "❌";
            }
        });
}








function consolidarTotales() {
    const orion = getInputValue("manualOrion");
    const aister = getInputValue("manualAister");

    const resultado =
        getById("ocr-consolidado-resultado") ||
        getById("ocr-result-content");

    if (!orion && !aister) {
        alert("Ingrese los totales manualmente o procese OCR antes de consolidar.");
        return;
    }

    const formData = new FormData();
    formData.append("orion", orion);
    formData.append("aister", aister);

    if (resultado) {
        resultado.innerHTML = htmlLoading("Consolidando totales...");
    }

    postFormTexto("/accion/consolidar-totales", formData)
        .then((html) => {
            setTotalesMonitorOrion(orion, aister);

            if (resultado) {
                resultado.innerHTML = html;
            }
        })
        .catch((err) => {
            if (resultado) {
                resultado.innerHTML = htmlError(`Error: ${err}`);
            } else {
                alert(`Error: ${err}`);
            }
        });
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


function insertarDatos(tipo) {
    const panelId = `panel-carga-${tipo === "lote" ? "lote" : tipo}`;
    const panel = getById(panelId);
    const boton = getById(`btn-insertar-${tipo === "lote" ? "lotes" : tipo}`);
    const fecha = obtenerFechaProcesoOrion();

    if (!fecha) {
        alert("Ingrese una fecha válida antes de insertar datos.");
        return;
    }

    if (conexionActiva === "remoto") {
        const confirmar = confirm(
            "Está a punto de insertar en REMOTO/Producción. ¿Desea continuar?"
        );

        if (!confirmar) {
            return;
        }
    }

    if (panel) {
        panel.open = true;
        insertarResultadoEnPanelMonitor(
            panel,
            htmlLoading(`Insertando consolidado ${tipo}...`)
        );
    }

    const formData = new FormData();
    formData.append("tipo", tipo);
    formData.append("conexion", conexionActiva);
    formData.append("fecha", fecha);

    postFormTexto("/accion/insertar-datos", formData)
        .then((html) => {
            const exito = esRespuestaExitosa(html);

            if (panel) {
                insertarResultadoEnPanelMonitor(panel, html);
            }

            actualizarIconoBoton(boton, exito);
        })
        .catch((err) => {
            if (panel) {
                insertarResultadoEnPanelMonitor(
                    panel,
                    htmlError(`Error: ${err}`)
                );
            }

            actualizarIconoBoton(boton, false);
        });
}






function obtenerFechaProcesoOrion() {
    const fecha = normalizarFechaOrion(getInputValue("fechaInput"));

    if (fecha) {
        setValue("fechaInput", fecha);
    }

    return fecha;
}

function obtenerCuerpoPanelMonitor(panel) {
    if (!panel) {
        return null;
    }

    if (panel.classList && panel.classList.contains("panel-body")) {
        return panel;
    }

    const cuerpoDirecto = panel.querySelector(":scope > .panel-body");

    if (cuerpoDirecto) {
        return cuerpoDirecto;
    }

    const cuerpo = panel.querySelector(".panel-body");

    if (cuerpo) {
        return cuerpo;
    }

    return panel;
}

function insertarResultadoEnPanelMonitor(panel, html) {
    const cuerpo = obtenerCuerpoPanelMonitor(panel);

    if (!cuerpo) {
        return;
    }

    cuerpo.innerHTML = html;
}

function verificarCarga(tipo) {
    const panelId = `panel-carga-${tipo === "lote" ? "lote" : tipo}`;
    const panel = getById(panelId);
    const boton = getById(`btn-carga-${tipo === "lote" ? "lotes" : tipo}`);
    const fecha = obtenerFechaProcesoOrion();

    if (!fecha) {
        alert("Ingrese una fecha válida antes de verificar la carga.");
        return;
    }

    if (panel) {
        panel.open = true;
        insertarResultadoEnPanelMonitor(
            panel,
            htmlLoading(`Verificando consolidado ${tipo}...`)
        );
    }

    const formData = new FormData();
    formData.append("tipo", tipo);
    formData.append("conexion", conexionActiva);
    formData.append("fecha", fecha);

    postFormTexto("/accion/verificar-carga", formData)
        .then((html) => {
            const exito = esRespuestaExitosa(html);

            if (panel) {
                insertarResultadoEnPanelMonitor(panel, html);
            }

            actualizarIconoBoton(boton, exito);
        })
        .catch((err) => {
            if (panel) {
                insertarResultadoEnPanelMonitor(
                    panel,
                    htmlError(`Error: ${err}`)
                );
            }

            actualizarIconoBoton(boton, false);
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
window.setModoOcrOrion = setModoOcrOrion;
window.mostrarModoOcrOrion = mostrarModoOcrOrion;
window.mostrarModoManualOrion = mostrarModoManualOrion;
window.activarOProcesarOcrOrion = activarOProcesarOcrOrion;
window.setTotalesMonitorOrion = setTotalesMonitorOrion;
window.actualizarNombreArchivosOcr = actualizarNombreArchivosOcr;
window.obtenerFechaProcesoOrion = obtenerFechaProcesoOrion;
window.obtenerCuerpoPanelMonitor = obtenerCuerpoPanelMonitor;
window.insertarResultadoEnPanelMonitor = insertarResultadoEnPanelMonitor;

/* ============================================================
   ORION - TRACKER VISUAL DE FASES A-G
   ============================================================ */

const ORION_PHASE_STATUS_KEY = "orionDiario.ui.orion.phaseStatus";

const ORION_PHASES = {
    A: "Crear carpetas",
    B: "Verificar red",
    C: "OCR y Totales",
    D: "Distribuir archivos",
    F: "Procesamiento",
    G: "Carga consolidados",
};

const ORION_ACTION_PHASES = {
    subirOCR: "C",
    consolidarTotales: "C",

    copiarDistribucionSeleccionada: "D",

    probarConexion: "G",
    seleccionarConexion: "G",
    verificarCarga: "G",
    insertarDatos: "G",
};

function estadoFaseOrionDefault() {
    const estado = {};

    Object.keys(ORION_PHASES).forEach((fase) => {
        estado[fase] = {
            status: "pending",
            detail: "Pendiente",
            updatedAt: "",
        };
    });

    return estado;
}

function leerEstadoFasesOrion() {
    try {
        const raw = localStorage.getItem(ORION_PHASE_STATUS_KEY);

        if (!raw) {
            return estadoFaseOrionDefault();
        }

        return {
            ...estadoFaseOrionDefault(),
            ...JSON.parse(raw),
        };
    } catch {
        return estadoFaseOrionDefault();
    }
}

function guardarEstadoFasesOrion(estado) {
    localStorage.setItem(ORION_PHASE_STATUS_KEY, JSON.stringify(estado));
}

function metaEstadoFaseOrion(status) {
    const meta = {
        pending: {
            icon: "⚪",
            label: "Pendiente",
            cls: "pending",
        },
        running: {
            icon: "⚙️",
            label: "Ejecutando",
            cls: "running",
        },
        done: {
            icon: "✅",
            label: "Completado",
            cls: "done",
        },
        error: {
            icon: "❌",
            label: "Error",
            cls: "error",
        },
        info: {
            icon: "ℹ️",
            label: "Revisar",
            cls: "info",
        },
    };

    return meta[status] || meta.pending;
}

function actualizarEstadoFaseOrion(fase, status, detail = "") {
    if (!ORION_PHASES[fase]) {
        return;
    }

    const estado = leerEstadoFasesOrion();
    const meta = metaEstadoFaseOrion(status);

    estado[fase] = {
        status,
        detail: detail || meta.label,
        updatedAt: new Date().toLocaleTimeString(),
    };

    guardarEstadoFasesOrion(estado);
    renderizarEstadoFasesOrion();
}

function evaluarEstadoDesdeHtmlOrion(html) {
    const texto = String(html || "").toLowerCase();

    if (
        texto.includes("traceback") ||
        texto.includes("error") ||
        texto.includes("❌") ||
        texto.includes("no encontrado")
    ) {
        return "error";
    }

    if (
        texto.includes("procesando") ||
        texto.includes("cargando") ||
        texto.includes("ejecutando") ||
        texto.includes("verificando") ||
        texto.includes("insertando")
    ) {
        return "running";
    }

    if (
        texto.includes("pendiente") ||
        texto.includes("sin ejecutar") ||
        texto.includes("no ejecutado")
    ) {
        return "pending";
    }

    if (
        texto.includes("correctamente") ||
        texto.includes("completado") ||
        texto.includes("insertado") ||
        texto.includes("insertados") ||
        texto.includes("validado") ||
        texto.includes("ok") ||
        texto.includes("✅")
    ) {
        return "done";
    }

    if (texto.trim()) {
        return "info";
    }

    return "pending";
}

function obtenerContenedorSidebarOrion() {
    if (typeof obtenerSidebarPrincipal === "function") {
        return obtenerSidebarPrincipal();
    }

    return (
        document.querySelector(".sidebar") ||
        document.querySelector("#sidebar") ||
        document.querySelector("aside")
    );
}

function obtenerContenedorMonitorOrion() {
    if (typeof obtenerMonitorCentral === "function") {
        return obtenerMonitorCentral();
    }

    return (
        document.querySelector(".monitor") ||
        document.querySelector("#monitor")
    );
}

function construirHtmlEstadoFasesOrion() {
    const estado = leerEstadoFasesOrion();

    const items = Object.entries(ORION_PHASES)
        .map(([fase, titulo]) => {
            const item = estado[fase] || {};
            const meta = metaEstadoFaseOrion(item.status);

            return `
                <div class="orion-phase-status-item ${meta.cls}" data-orion-phase="${fase}">
                    <span class="orion-phase-letter">${fase}</span>
                    <span class="orion-phase-name">${titulo}</span>
                    <span class="orion-phase-state">${meta.icon} ${meta.label}</span>
                </div>
            `;
        })
        .join("");

    return `
        <div id="orion-phase-sidebar-status" class="orion-phase-status-card">
            <div class="orion-phase-status-title">
                🧭 Estado de fases ORION
            </div>
            <div class="orion-phase-status-list">
                ${items}
            </div>
        </div>
    `;
}

function esVistaOrionActiva() {
    const modulo = localStorage.getItem("moduloActivoOrionDiario") || "orion";
    return modulo === "orion";
}

function asegurarPanelEstadoSidebarOrion() {
    if (!esVistaOrionActiva()) {
        return;
    }

    const sidebar = obtenerContenedorSidebarOrion();

    if (!sidebar) {
        return;
    }

    const existe = document.getElementById("orion-phase-sidebar-status");

    if (existe) {
        return;
    }

    sidebar.insertAdjacentHTML("afterbegin", construirHtmlEstadoFasesOrion());
}

function actualizarPanelEstadoSidebarOrion() {
    const actual = document.getElementById("orion-phase-sidebar-status");

    if (!actual) {
        asegurarPanelEstadoSidebarOrion();
        return;
    }

    actual.outerHTML = construirHtmlEstadoFasesOrion();
}

function faseOrionDesdeSummary(summary) {
    const accion = accionOrionDesdeSummary(summary);

    if (accion) {
        return faseOrionDesdeAccion(accion);
    }

    const texto = String(summary?.textContent || "").toLowerCase();

    if (
        texto.includes("carga") ||
        texto.includes("consolidado") ||
        texto.includes("insert")
    ) {
        return "G";
    }

    if (
        texto.includes("discador") ||
        texto.includes("causales") ||
        texto.includes("lotes") ||
        texto.includes("comparar") ||
        texto.includes("proces")
    ) {
        return "F";
    }

    return "";
}






/* ============================================================
   ORION - ESTADO INDIVIDUAL POR PANEL
   ============================================================ */

const ORION_ACTION_STATUS_KEY = "orionDiario.ui.orion.actionStatus";

const ORION_ACTION_LABELS = {
    "crear-carpetas": "Crear Carpetas",
    "verificar-red": "Verificar Red",
    "ocr-totales": "OCR y Totales",
    "distribuir": "Distribuir Archivos",

    "procesar-discador": "Procesar Discador",
    "procesar-causales": "Procesar Causales",
    "procesar-lotes": "Procesar Lotes",
    "comparar-lotes": "Comparar Lotes",

    "carga-causales": "Carga Causales",
    "carga-lotes": "Carga Lotes",
    "carga-discador": "Carga Discador",
    "consolidado-gestion": "Consolidado Gestión Orion",
};

const ORION_ACTION_TO_PHASE = {
    "crear-carpetas": "A",
    "verificar-red": "B",
    "ocr-totales": "C",
    "distribuir": "D",

    "procesar-discador": "F",
    "procesar-causales": "F",
    "procesar-lotes": "F",
    "comparar-lotes": "F",

    "carga-causales": "G",
    "carga-lotes": "G",
    "carga-discador": "G",
    "consolidado-gestion": "G",
};

const ORION_PHASE_ACTIONS = {
    A: ["crear-carpetas"],
    B: ["verificar-red"],
    C: ["ocr-totales"],
    D: ["distribuir"],
    F: [
        "procesar-discador",
        "procesar-causales",
        "procesar-lotes",
        "comparar-lotes",
    ],
    G: [
        "carga-causales",
        "carga-lotes",
        "carga-discador",
        "consolidado-gestion",
    ],
};

function estadoAccionesOrionDefault() {
    const estado = {};

    Object.keys(ORION_ACTION_LABELS).forEach((accion) => {
        estado[accion] = {
            status: "pending",
            detail: "Pendiente",
            updatedAt: "",
        };
    });

    return estado;
}

function leerEstadoAccionesOrion() {
    try {
        const raw = localStorage.getItem(ORION_ACTION_STATUS_KEY);

        if (!raw) {
            return estadoAccionesOrionDefault();
        }

        return {
            ...estadoAccionesOrionDefault(),
            ...JSON.parse(raw),
        };
    } catch {
        return estadoAccionesOrionDefault();
    }
}

function guardarEstadoAccionesOrion(estado) {
    localStorage.setItem(ORION_ACTION_STATUS_KEY, JSON.stringify(estado));
}

function accionOrionDesdeSummary(summary) {
    const texto = String(summary?.textContent || "").toLowerCase();

    if (texto.includes("carga causales")) {
        return "carga-causales";
    }

    if (texto.includes("carga lotes")) {
        return "carga-lotes";
    }

    if (texto.includes("carga discador")) {
        return "carga-discador";
    }

    if (texto.includes("consolidado gestión") || texto.includes("consolidado gestion")) {
        return "consolidado-gestion";
    }

    if (texto.includes("crear carpetas")) {
        return "crear-carpetas";
    }

    if (texto.includes("verificar red")) {
        return "verificar-red";
    }

    if (texto.includes("ocr") || texto.includes("totales")) {
        return "ocr-totales";
    }

    if (texto.includes("distribuir")) {
        return "distribuir";
    }

    if (texto.includes("procesar discador")) {
        return "procesar-discador";
    }

    if (texto.includes("procesar causales")) {
        return "procesar-causales";
    }

    if (texto.includes("procesar lotes")) {
        return "procesar-lotes";
    }

    if (texto.includes("comparar lotes")) {
        return "comparar-lotes";
    }

    return "";
}

function faseOrionDesdeAccion(accion) {
    return ORION_ACTION_TO_PHASE[accion] || "";
}

function recalcularEstadoFaseOrionDesdeAcciones(fase) {
    const acciones = ORION_PHASE_ACTIONS[fase] || [];

    if (!acciones.length) {
        return;
    }

    const estadoAcciones = leerEstadoAccionesOrion();
    const estados = acciones.map((accion) => {
        return estadoAcciones[accion]?.status || "pending";
    });

    let status = "pending";
    let detail = "Pendiente";

    if (estados.includes("running")) {
        status = "running";
        detail = "Ejecutando";
    } else if (estados.includes("error")) {
        status = "error";
        detail = "Error";
    } else if (estados.every((item) => item === "done")) {
        status = "done";
        detail = "Completado";
    } else if (estados.some((item) => item === "done" || item === "info")) {
        status = "info";
        detail = "Parcial";
    }

    const estadoFases = leerEstadoFasesOrion();

    estadoFases[fase] = {
        status,
        detail,
        updatedAt: new Date().toLocaleTimeString(),
    };

    guardarEstadoFasesOrion(estadoFases);
}

function actualizarEstadoAccionOrion(accionRaw, status, detail = "") {
    const accion = normalizarAccionOrion(accionRaw);

    if (!ORION_ACTION_LABELS[accion]) {
        return false;
    }

    const estado = leerEstadoAccionesOrion();
    const meta = metaEstadoFaseOrion(status);

    estado[accion] = {
        status,
        detail: detail || meta.label,
        updatedAt: new Date().toLocaleTimeString(),
    };

    guardarEstadoAccionesOrion(estado);

    const fase = faseOrionDesdeAccion(accion);

    if (fase) {
        recalcularEstadoFaseOrionDesdeAcciones(fase);
    }

    renderizarEstadoFasesOrion();

    return true;
}

function actualizarEstadoOperacionOrion(accionRaw, fase, status, detail = "") {
    const accion = normalizarAccionOrion(accionRaw);

    if (actualizarEstadoAccionOrion(accion, status, detail)) {
        return;
    }

    if (fase && typeof actualizarEstadoFaseOrion === "function") {
        actualizarEstadoFaseOrion(fase, status, detail);
    }
}


function decorarHeadersMonitorOrion() {
    if (!esVistaOrionActiva()) {
        return;
    }

    const monitor = obtenerContenedorMonitorOrion();

    if (!monitor) {
        return;
    }

    const estadoFases = leerEstadoFasesOrion();
    const estadoAcciones = leerEstadoAccionesOrion();

    monitor.querySelectorAll(".panel-monitor > summary").forEach((summary) => {
        if (summary.closest('[data-orion-workflow-managed="1"]')) {
            return;
        }

        const accion = accionOrionDesdeSummary(summary);
        const fase = faseOrionDesdeSummary(summary);

        let item = null;

        if (accion && ORION_ACTION_LABELS[accion]) {
            item = estadoAcciones[accion] || {};
        } else if (fase && ORION_PHASES[fase]) {
            item = estadoFases[fase] || {};
        } else {
            return;
        }

        let chip = summary.querySelector(".orion-phase-header-chip");

        if (!chip) {
            chip = document.createElement("span");
            chip.className = "orion-phase-header-chip";
            summary.appendChild(chip);
        }

        const meta = metaEstadoFaseOrion(item.status);

        chip.className = `orion-phase-header-chip ${meta.cls}`;
        chip.textContent = `${meta.icon} ${meta.label}`;
        chip.title = item.updatedAt
            ? `${item.detail || meta.label} - ${item.updatedAt}`
            : item.detail || meta.label;
    });
}



function renderizarEstadoFasesOrion() {
    actualizarPanelEstadoSidebarOrion();
    decorarHeadersMonitorOrion();
}

function faseOrionDesdeArgumentos(args) {
    const texto = args.map((item) => String(item || "")).join(" ").toLowerCase();

    if (texto.includes("crear") || texto.includes("carpeta")) {
        return "A";
    }

    if (texto.includes("red")) {
        return "B";
    }

    if (texto.includes("ocr") || texto.includes("total")) {
        return "C";
    }

    if (texto.includes("distrib")) {
        return "D";
    }

    if (
        texto.includes("discador") ||
        texto.includes("causales") ||
        texto.includes("lote") ||
        texto.includes("compar") ||
        texto.includes("proces")
    ) {
        return "F";
    }

    if (
        texto.includes("carga") ||
        texto.includes("insert") ||
        texto.includes("verificar")
    ) {
        return "G";
    }

    return "";
}





function envolverAccionOrion(nombreFuncion, faseFija = "") {
    const original = window[nombreFuncion];

    if (typeof original !== "function") {
        return;
    }

    if (original.__orionPhaseWrapped) {
        return;
    }

    const envuelta = function (...args) {
        const fase = faseFija || faseOrionDesdeArgumentos(args);

        if (fase) {
            actualizarEstadoFaseOrion(fase, "running", "Ejecutando acción...");
        }

        try {
            const resultado = original.apply(this, args);
            return resultado;
        } catch (error) {
            if (fase) {
                actualizarEstadoFaseOrion(
                    fase,
                    "error",
                    error?.message || "Error en acción"
                );
            }

            throw error;
        }
    };

    envuelta.__orionPhaseWrapped = true;
    window[nombreFuncion] = envuelta;
}

function envolverAccionesFasesOrion() {
    Object.entries(ORION_ACTION_PHASES).forEach(([nombreFuncion, fase]) => {
        envolverAccionOrion(nombreFuncion, fase);
    });

    envolverAccionOrion("ejecutarAccion", "");
}

function observarPanelesOrion() {
    const monitor = obtenerContenedorMonitorOrion();

    if (!monitor || !esVistaOrionActiva()) {
        return;
    }

    monitor.querySelectorAll(".panel-monitor").forEach((panel) => {
        if (panel.dataset.orionWorkflowManaged === "1") {
            return;
        }

        if (panel.getAttribute("data-orion-workflow-managed") === "1") {
            return;
        }

        if (panel.dataset.orionObserver === "1") {
            return;
        }

        panel.dataset.orionObserver = "1";

        const summary = panel.querySelector(":scope > summary");
        const accion = accionOrionDesdeSummary(summary);
        const fase = faseOrionDesdeSummary(summary);

        if (!accion && !fase) {
            return;
        }

        const body =
            panel.querySelector(":scope > .panel-body") ||
            panel.querySelector(".panel-body");

        if (!body) {
            return;
        }

        const aplicar = () => {
            const estado = evaluarEstadoDesdeHtmlOrion(body.innerHTML);
            const meta = metaEstadoFaseOrion(estado);

            if (accion && ORION_ACTION_LABELS[accion]) {
                actualizarEstadoAccionOrion(accion, estado, meta.label);
                return;
            }

            if (fase && estado !== "pending") {
                actualizarEstadoFaseOrion(fase, estado, meta.label);
            }
        };

        const observer = new MutationObserver(() => {
            aplicar();
        });

        observer.observe(body, {
            childList: true,
            subtree: true,
            characterData: true,
        });

        aplicar();
    });
}



function inicializarEstadoFasesOrion() {
    if (!esVistaOrionActiva()) {
        return;
    }

    envolverAccionesFasesOrion();
    asegurarPanelEstadoSidebarOrion();
    observarPanelesOrion();
    renderizarEstadoFasesOrion();
}

function programarInicializacionEstadoFasesOrion() {
    setTimeout(inicializarEstadoFasesOrion, 50);
    setTimeout(inicializarEstadoFasesOrion, 350);
    setTimeout(inicializarEstadoFasesOrion, 900);
}

if (!window.__orionSeleccionarModuloWrapped) {
    window.__orionSeleccionarModuloWrapped = true;

    const seleccionarModuloOriginalOrionStatus = window.seleccionarModulo;

    if (typeof seleccionarModuloOriginalOrionStatus === "function") {
        window.seleccionarModulo = function (modulo) {
            const resultado = seleccionarModuloOriginalOrionStatus.apply(this, arguments);

            if (!modulo || modulo === "orion") {
                programarInicializacionEstadoFasesOrion();
            }

            return resultado;
        };
    }
}

document.addEventListener("DOMContentLoaded", () => {
    programarInicializacionEstadoFasesOrion();
});

window.actualizarEstadoFaseOrion = actualizarEstadoFaseOrion;
window.renderizarEstadoFasesOrion = renderizarEstadoFasesOrion;
window.inicializarEstadoFasesOrion = inicializarEstadoFasesOrion;

function sincronizarFechaOrionPanel(valor) {
    const fecha = String(valor || "").trim();

    const principal = getById("fechaInput");
    const panelCrear = getById("fechaInputPanelCrear");

    if (principal && principal.value !== fecha) {
        principal.value = fecha;
    }

    if (panelCrear && panelCrear.value !== fecha) {
        panelCrear.value = fecha;
    }

    if (typeof persistirEstadoInputsVisibles === "function") {
        persistirEstadoInputsVisibles();
    }
}

function sincronizarFechaOrionPanelDesdePrincipal() {
    const principal = getById("fechaInput");
    const panelCrear = getById("fechaInputPanelCrear");

    if (principal && panelCrear && panelCrear.value !== principal.value) {
        panelCrear.value = principal.value;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    setTimeout(sincronizarFechaOrionPanelDesdePrincipal, 100);
    setTimeout(sincronizarFechaOrionPanelDesdePrincipal, 600);
});
window.sincronizarFechaOrionPanel = sincronizarFechaOrionPanel;
window.sincronizarFechaOrionPanelDesdePrincipal = sincronizarFechaOrionPanelDesdePrincipal;
window.wrapperPanelAccionOrion = wrapperPanelAccionOrion;
window.abrirPanelAccionOrion = abrirPanelAccionOrion;
window.prepararYEjecutarAccionOrion = prepararYEjecutarAccionOrion;
window.resultadoPanelAccionOrion = resultadoPanelAccionOrion;
window.fasePorAccionOrion = fasePorAccionOrion;
window.normalizarAccionOrion = normalizarAccionOrion;
window.botonesRelacionadosAccionOrion = botonesRelacionadosAccionOrion;
window.actualizarBotonesAccionOrion = actualizarBotonesAccionOrion;
window.contenedorScrollMonitorOrion = contenedorScrollMonitorOrion;
window.panelCentralAccionOrion = panelCentralAccionOrion;
window.resaltarPanelCentralOrion = resaltarPanelCentralOrion;

/* ============================================================
   ORION - SIDEBAR ABRE PANEL CENTRAL DIRECTO
   ============================================================ */

function buscarPanelCentralOrionPorTexto(textoBuscado) {
    const textoObjetivo = String(textoBuscado || "").toLowerCase();

    const panels = document.querySelectorAll("details.panel-monitor, .panel-monitor");

    for (const panel of panels) {
        const summary = panel.querySelector(":scope > summary") || panel.querySelector("summary");
        const texto = String(summary?.textContent || "").toLowerCase();

        if (texto.includes(textoObjetivo)) {
            return panel;
        }
    }

    return null;
}

function abrirPanelCentralOrionDirecto(accionRaw) {
    const accion = normalizarAccionOrion(accionRaw);

    const mapaTexto = {
        "crear-carpetas": "crear carpetas",
        "verificar-red": "verificar red",
        "distribuir": "distribuir archivos",
        "ocr-subir": "ocr y totales",
        "procesar-discador": "procesar discador",
        "procesar-causales": "procesar causales",
        "procesar-lotes": "procesar lotes",
        "comparar-lotes": "comparar lotes",
    };

    const texto = mapaTexto[accion] || accion;
    const panel = buscarPanelCentralOrionPorTexto(texto);

    if (!panel) {
        console.warn("No se encontró panel central ORION para:", accionRaw);
        return null;
    }

    if (panel.tagName && panel.tagName.toLowerCase() === "details") {
        panel.open = true;
    }

    panel.classList.remove("orion-panel-focus-flash");
    void panel.offsetWidth;
    panel.classList.add("orion-panel-focus-flash");

    setTimeout(() => {
        panel.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
    }, 50);

    setTimeout(() => {
        panel.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
    }, 350);

    return panel;
}



function abrirYEjecutarOrionSidebar(accion, boton = null) {
    abrirPanelCentralOrionDirecto(accion);

    setTimeout(() => {
        abrirPanelCentralOrionDirecto(accion);
    }, 250);

    return ejecutarAccion(accion, boton);
}

function registrarClickSidebarOrionDirecto() {
    if (window.__orionSidebarDirectOpenRegistered) {
        return;
    }

    window.__orionSidebarDirectOpenRegistered = true;

    document.addEventListener(
        "click",
        (event) => {
            const boton = event.target?.closest?.("button");

            if (!boton) {
                return;
            }

            const texto = String(boton.textContent || "").toLowerCase();
            const onclick = String(boton.getAttribute("onclick") || "").toLowerCase();

            const esCrear =
                texto.includes("crear carpetas") ||
                onclick.includes("crear-carpetas");

            const esRed =
                texto.includes("verificar red") ||
                onclick.includes("verificar-red");

            if (!esCrear && !esRed) {
                return;
            }

            const estaEnSidebar =
                boton.closest(".sidebar") ||
                boton.closest("#sidebar") ||
                boton.closest("aside") ||
                boton.closest(".sidebar-columns");

            if (!estaEnSidebar) {
                return;
            }

            const accion = esCrear ? "crear-carpetas" : "verificar-red";

            abrirPanelCentralOrionDirecto(accion);

            setTimeout(() => {
                abrirPanelCentralOrionDirecto(accion);
            }, 300);
        },
        true
    );
}

document.addEventListener("DOMContentLoaded", () => {
    registrarClickSidebarOrionDirecto();
});

window.buscarPanelCentralOrionPorTexto = buscarPanelCentralOrionPorTexto;
window.abrirPanelCentralOrionDirecto = abrirPanelCentralOrionDirecto;
window.abrirYEjecutarOrionSidebar = abrirYEjecutarOrionSidebar;
window.registrarClickSidebarOrionDirecto = registrarClickSidebarOrionDirecto;

/* ============================================================
   ORION LEGACY COMPATIBILITY - DISTRIBUCIÓN
   Estas funciones evitan ReferenceError de exports antiguos.
   La Fase D real ahora la controla app/static/js/orion_workflow.js
   ============================================================ */













window.accionOrionDesdeSummary = accionOrionDesdeSummary;
window.faseOrionDesdeAccion = faseOrionDesdeAccion;
window.leerEstadoAccionesOrion = leerEstadoAccionesOrion;
window.guardarEstadoAccionesOrion = guardarEstadoAccionesOrion;
window.actualizarEstadoAccionOrion = actualizarEstadoAccionOrion;
window.actualizarEstadoOperacionOrion = actualizarEstadoOperacionOrion;
window.recalcularEstadoFaseOrionDesdeAcciones = recalcularEstadoFaseOrionDesdeAcciones;

/* ============================================================
   ORION LEGACY COMPATIBILITY CANÓNICO
   Funciones únicas para compatibilidad con flujo anterior.
   La ejecución principal ORION está controlada por orion_workflow.js.
   ============================================================ */

function obtenerPanelResultadoDistribucionOrion() {
    return (
        document.getElementById("panel-distribuir") ||
        document.querySelector("#panel-distribuir-wrapper .orion-result-content") ||
        document.querySelector("#panel-distribuir-wrapper .panel-body") ||
        document.querySelector("#panel-distribuir-wrapper")
    );
}

function obtenerChecksDistribucionOrion() {
    const root =
        document.getElementById("panel-distribuir") ||
        document.getElementById("panel-distribuir-wrapper") ||
        document;

    return Array.from(root.querySelectorAll("input[type='checkbox']:checked"));
}

function valorCheckboxDistribucionOrion(check) {
    if (!check) {
        return "";
    }

    const row = check.closest ? check.closest("tr") : null;

    const candidatos = [
        check.dataset?.archivo,
        check.dataset?.ruta,
        check.dataset?.path,
        check.dataset?.file,
        check.dataset?.nombre,
        check.dataset?.name,
        row?.dataset?.archivo,
        row?.dataset?.ruta,
        row?.dataset?.path,
        check.value,
    ];

    const valor = candidatos
        .map((item) => String(item || "").trim())
        .find((item) => item && item.toLowerCase() !== "on");

    return valor || "";
}

function obtenerSeleccionadosDistribucionOrion() {
    return obtenerChecksDistribucionOrion()
        .map((check) => {
            const row = check.closest ? check.closest("tr") : null;

            return {
                categoria:
                    check.dataset?.categoria ||
                    row?.dataset?.categoria ||
                    "",
                archivo: valorCheckboxDistribucionOrion(check),
            };
        })
        .filter((item) => {
            return item.categoria && item.archivo;
        });
}

function htmlEsNotFoundOrion(html) {
    const texto = String(html || "").toLowerCase();

    return (
        texto.includes("not found") ||
        texto.includes("404") ||
        texto.includes("requested url was not found")
    );
}

function actualizarEstadoDistribucionOrionDesdeHtml(html) {
    const exito =
        typeof esRespuestaExitosa === "function"
            ? esRespuestaExitosa(html)
            : !htmlEsNotFoundOrion(html);

    if (typeof actualizarEstadoFaseOrion === "function") {
        actualizarEstadoFaseOrion(
            "D",
            exito ? "done" : "error",
            exito ? "Completado" : "Error"
        );
    }

    if (typeof actualizarEstadoFaseDDirecto === "function") {
        try {
            actualizarEstadoFaseDDirecto();
        } catch {
            // Compatibilidad visual únicamente.
        }
    }

    return exito;
}

function mostrarIngresoManualOrion() {
    if (typeof mostrarModoManualWorkflow === "function") {
        mostrarModoManualWorkflow();
        return;
    }

    if (
        typeof mostrarModoManualOrion === "function" &&
        mostrarModoManualOrion !== mostrarIngresoManualOrion
    ) {
        mostrarModoManualOrion();
        return;
    }

    const manual = document.getElementById("manual-totales");

    if (manual) {
        manual.style.display = "block";
        manual.classList.add("active");
    }

    const ocr = document.getElementById("orion-ocr-mode");

    if (ocr) {
        ocr.classList.remove("active");
    }
}

window.obtenerPanelResultadoDistribucionOrion = obtenerPanelResultadoDistribucionOrion;
window.obtenerChecksDistribucionOrion = obtenerChecksDistribucionOrion;
window.valorCheckboxDistribucionOrion = valorCheckboxDistribucionOrion;
window.obtenerSeleccionadosDistribucionOrion = obtenerSeleccionadosDistribucionOrion;
window.actualizarEstadoDistribucionOrionDesdeHtml = actualizarEstadoDistribucionOrionDesdeHtml;
window.htmlEsNotFoundOrion = htmlEsNotFoundOrion;
window.mostrarIngresoManualOrion = mostrarIngresoManualOrion;
