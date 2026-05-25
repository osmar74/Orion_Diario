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

function mostrarIngresoManualOrion() {
    mostrarModoManualOrion();
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






function mostrarIngresoManualOrion() {
    const manualDiv = getById("manual-totales");
    const panel = getById("panel-ocr");

    if (panel) {
        panel.open = true;
    }

    if (manualDiv) {
        manualDiv.style.display = "block";
        manualDiv.scrollIntoView({
            behavior: "smooth",
            block: "center",
        });
    }
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
window.mostrarIngresoManualOrion = mostrarIngresoManualOrion;
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
    E: "Procesamiento",
    F: "Comparación",
    G: "Carga consolidados",
};

const ORION_ACTION_PHASES = {
    subirOCR: "C",
    consolidarTotales: "C",

    copiarDistribucionSeleccionada: "D",

    actualizarEstadoDiscador: "E",
    actualizarCuadre: "E",

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
    const texto = String(summary?.textContent || "").toLowerCase();

    if (texto.includes("crear") || texto.includes("carpeta")) {
        return "A";
    }

    if (texto.includes("red")) {
        return "B";
    }

    if (texto.includes("ocr") || texto.includes("totales")) {
        return "C";
    }

    if (texto.includes("distribuir") || texto.includes("distribución")) {
        return "D";
    }

    if (
        texto.includes("discador") ||
        texto.includes("causales") ||
        texto.includes("lotes") ||
        texto.includes("proces")
    ) {
        return "E";
    }

    if (texto.includes("compar")) {
        return "F";
    }

    if (
        texto.includes("carga") ||
        texto.includes("consolidado") ||
        texto.includes("insert")
    ) {
        return "G";
    }

    return "";
}

function decorarHeadersMonitorOrion() {
    if (!esVistaOrionActiva()) {
        return;
    }

    const monitor = obtenerContenedorMonitorOrion();

    if (!monitor) {
        return;
    }

    const estado = leerEstadoFasesOrion();

    monitor.querySelectorAll(".panel-monitor > summary").forEach((summary) => {
        const fase = faseOrionDesdeSummary(summary);

        if (!fase || !ORION_PHASES[fase]) {
            return;
        }

        let chip = summary.querySelector(".orion-phase-header-chip");

        if (!chip) {
            chip = document.createElement("span");
            chip.className = "orion-phase-header-chip";
            summary.appendChild(chip);
        }

        const item = estado[fase] || {};
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
        texto.includes("proces")
    ) {
        return "E";
    }

    if (texto.includes("compar")) {
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
        if (panel.dataset.orionObserver === "1") {
            return;
        }

        panel.dataset.orionObserver = "1";

        const summary = panel.querySelector(":scope > summary");
        const fase = faseOrionDesdeSummary(summary);

        if (!fase) {
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

            if (estado !== "pending") {
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
