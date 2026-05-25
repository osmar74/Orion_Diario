/* ============================================================
   ORION PROCESOS - LÓGICA DE FRONTEND (main.js)
   ============================================================ */

/* ---------- VARIABLES GLOBALES ---------- */

let conexionActiva = "local"; // "local" o "remoto"
let conexionConsolidado = "local"; // conexión independiente del consolidado

const panelMap = {
    "crear-carpetas": "panel-crear",
    "verificar-red": "panel-verificar",
    "distribuir": "panel-distribuir",
    "discador": "panel-discador",
    "causales": "panel-causales",
    "comparar-lotes": "panel-comparar",
    "lotes": "panel-lotes",
};

const pasoMap = {
    "crear-carpetas": "crear",
    "verificar-red": "verificar",
    "distribuir": "distribuir",
    "discador": "discador",
    "causales": "causales",
    "lotes": "lotes",
    "comparar-lotes": null,
};

/* ---------- UTILIDADES GENERALES ---------- */

function getById(id) {
    return document.getElementById(id);
}

function normalizar(texto) {
    return String(texto || "")
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "");
}

function htmlLoading(mensaje) {
    return `<div class="log-line info">⏳ ${mensaje}</div>`;
}

function htmlError(mensaje) {
    return `<div class="log-line error">❌ ${mensaje}</div>`;
}

function esRespuestaExitosa(html) {
    return html.includes("log-line success") || html.includes("✅");
}

function setText(id, valor) {
    const elemento = getById(id);

    if (elemento) {
        elemento.textContent = valor;
    }
}

function setValue(id, valor) {
    const elemento = getById(id);

    if (elemento && "value" in elemento) {
        elemento.value = valor;
    }
}

function getInputValue(id) {
    const elemento = getById(id);

    if (elemento && "value" in elemento) {
        return elemento.value;
    }

    return "";
}

function normalizarFechaOrion(valor) {
    const limpio = String(valor || "").replace(/[^0-9]/g, "");

    if (limpio.length === 8) {
        return `${limpio.slice(0, 6)}_${limpio.slice(6, 8)}`;
    }

    return String(valor || "").trim();
}

function fetchTexto(url, opciones = {}) {
    return fetch(url, opciones).then((res) => res.text());
}

function postFormTexto(url, formData) {
    return fetchTexto(url, {
        method: "POST",
        body: formData,
    });
}

function buscarPanelPorUrl(url) {
    for (const [key, panelId] of Object.entries(panelMap)) {
        if (url.includes(key)) {
            return panelId;
        }
    }

    return null;
}

function actualizarIconoBoton(boton, exito) {
    if (!boton) return;

    const icono = boton.querySelector(".status-icon");

    if (icono) {
        icono.textContent = exito ? "✅" : "❌";
    }
}

/* ---------- MONITOR Y PANELES ---------- */

function insertarEnPanel(panelId, html, exito, subSelector = ".panel-body") {
    const panel = getById(panelId);

    if (!panel) return;

    const container = panel.querySelector(subSelector);

    if (!container) return;

    container.innerHTML = html;

    const icon = panel.querySelector(".panel-icon");

    if (icon) {
        icon.textContent = exito ? "✅" : "❌";
    }

    panel.open = true;
}

function actualizarTotalesHeader() {
    const orion = getById("totalOrion")?.textContent || "--";
    const aister = getById("totalAister")?.textContent || "--";

    setText("ocrOrion", orion);
    setText("ocrAister", aister);
}

function cerrarOtrosDetails(boton) {
    if (!boton) return;

    const sidebar = getById("sidebar");

    if (!sidebar) return;

    const abiertos = sidebar.querySelectorAll("details[open]");
    const miDetails = boton.closest("details");

    abiertos.forEach((details) => {
        if (details !== miDetails) {
            details.open = false;
        }
    });
}

function marcarPasoCompletado(paso) {
    if (!paso) return;

    const items = document.querySelectorAll(".timeline-item");
    const index = Array.from(items).findIndex(
        (item) => item.dataset.paso === paso
    );

    if (index === -1) return;

    items.forEach((item, i) => {
        const circle = item.querySelector(".timeline-circle");

        item.classList.remove("completado", "activo");

        if (circle) {
            circle.classList.remove("completado", "activo");
        }

        if (i < index) {
            item.classList.add("completado");

            if (circle) {
                circle.classList.add("completado");
            }
        } else if (i === index) {
            item.classList.add("activo");

            if (circle) {
                circle.classList.add("activo");
            }
        }
    });
}

function toggleSidebar() {
    const sidebar = getById("sidebar");

    if (sidebar) {
        sidebar.classList.toggle("collapsed");
    }
}

/* ---------- ACCIONES DE LAS FASES ---------- */

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

/* ---------- OCR ---------- */

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

/* ---------- CONEXIONES Y CARGA A SQL SERVER ---------- */

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

/* ---------- CONSOLIDADO ---------- */

function abrirConsolidado() {
    const panel = getById("panel-consolidado");

    if (panel) {
        panel.open = true;
    }
}

function seleccionarConexionConsolidado(tipo) {
    conexionConsolidado = tipo === "remoto" ? "remoto" : "local";

    const btnLocal = getById("btnConsLocal");
    const btnRemoto = getById("btnConsRemoto");

    if (btnLocal) {
        btnLocal.classList.toggle("active", conexionConsolidado === "local");
    }

    if (btnRemoto) {
        btnRemoto.classList.toggle("active", conexionConsolidado === "remoto");
    }

    const indicador = getById("cons-conexion-indicador");

    if (indicador) {
        indicador.textContent =
            conexionConsolidado === "local"
                ? "Local activo"
                : "Remoto activo";
    }

    fetchTexto(
        `/accion/probar-conexion-consolidado?conexion=${encodeURIComponent(
            conexionConsolidado
        )}`
    )
        .then((html) => {
            const badge = getById("badge-consolidado");
            const exito = esRespuestaExitosa(html);

            if (badge) {
                badge.className = exito
                    ? "badge-conexion badge-verde"
                    : "badge-conexion badge-rojo";

                badge.textContent = `${exito ? "✅" : "❌"} ${conexionConsolidado === "local" ? "Local" : "Remoto"
                    }`;
            }
        })
        .catch(() => {
            const badge = getById("badge-consolidado");

            if (badge) {
                badge.className = "badge-conexion badge-rojo";
                badge.textContent = `❌ ${conexionConsolidado === "local" ? "Local" : "Remoto"
                    }`;
            }
        });
}

function ejecutarConsultaConsolidado() {
    const resultado = getById("cons-resultado");

    if (!resultado) {
        alert("No se encontró el panel de resultado del consolidado.");
        return;
    }

    const fecha = getInputValue("consFecha");
    const meses = getInputValue("consMeses");

    if (!fecha || !meses) {
        alert("Debe ingresar fecha y mes de gestión.");
        return;
    }

    resultado.innerHTML = htmlLoading("Ejecutando consulta...");

    const formData = new FormData();
    formData.append("fecha", fecha);
    formData.append("meses", meses);
    formData.append("conexion", conexionConsolidado);

    postFormTexto("/accion/consolidar-consulta", formData)
        .then((html) => {
            resultado.innerHTML = html;
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error: ${err}`);
        });
}

function aplicarFiltroYExportar() {
    const resultado = getById("cons-resultado");

    if (!resultado) {
        alert("No se encontró el panel de resultado del consolidado.");
        return;
    }

    const checkboxes = resultado.querySelectorAll(
        'input[name="descripcion"]:checked'
    );

    const seleccionados = Array.from(checkboxes).map((checkbox) => {
        return checkbox.value || "";
    });

    const fecha = getInputValue("consFecha");
    const meses = getInputValue("consMeses");
    const tempId = getInputValue("cons-temp-id");

    if (!fecha || !tempId) {
        alert("Falta fecha o identificador temporal del consolidado.");
        return;
    }

    const formData = new FormData();
    formData.append("fecha", fecha);
    formData.append("meses", meses);
    formData.append("conexion", conexionConsolidado);
    formData.append("seleccionados", JSON.stringify(seleccionados));
    formData.append("temp_id", tempId);

    resultado.innerHTML = htmlLoading("Aplicando filtros y generando Excel...");

    postFormTexto("/accion/consolidar-aplicar", formData)
        .then((html) => {
            resultado.innerHTML = html;
        })
        .catch((err) => {
            resultado.innerHTML = htmlError(`Error: ${err}`);
        });
}

/* ---------- RESET ---------- */

function resetTodo() {
    if (!confirm("¿Está seguro de reiniciar todo el proceso?")) {
        return;
    }

    fetchTexto("/reset")
        .then(() => {
            document
                .querySelectorAll(".paso")
                .forEach((paso) =>
                    paso.classList.remove("completado", "activo")
                );

            document
                .querySelectorAll(".panel-icon")
                .forEach((icono) => {
                    icono.textContent = "⚪";
                });

            document
                .querySelectorAll(".panel-body")
                .forEach((body) => {
                    body.innerHTML = "Pendiente...";
                });

            document
                .querySelectorAll(".panel-monitor")
                .forEach((panel) => {
                    panel.open = false;
                });

            location.reload();
        })
        .catch(() => location.reload());
}

/* ---------- INICIALIZACIÓN ---------- */

document.addEventListener("DOMContentLoaded", () => {
    actualizarTotalesHeader();

    document.querySelectorAll(".panel-monitor").forEach((panel) => {
        panel.open = false;
    });

    actualizarBadgesConexion(false);
});


/* ============================================================
   SELECTOR TEMPORAL DE MÓDULOS
   ============================================================ */

const MODULOS_UI = {
    orion: {
        botonId: "btnModuloOrion",
        tituloMonitor: "Monitor de Ejecución",
    },
    aister: {
        botonId: "btnModuloAister",
        tituloSidebar: "Fases y Pasos de Gestión Diaria ASTER",
        tituloMonitor: "Monitor de ejecución de Gestión Diaria ASTER",
        descripcion:
            "Módulo para gestionar el proceso diario ASTER: captura del total, búsqueda del archivo After, normalización, conciliación de entidades e inserción final.",
    },
    consolidar: {
        botonId: "btnModuloConsolidar",
        tituloSidebar: "Fases y Pasos para Consolidar Gestión",
        tituloMonitor: "Monitor de ejecución de Consolidación de gestión",
        descripcion:
            "Este módulo queda reservado para consolidar gestiones. Momentáneamente no ejecuta procesos.",
        pasos: [
            "1. Selección de gestión",
            "2. Lectura de archivos consolidados",
            "3. Validación de datos",
            "4. Cruce de información",
            "5. Exportación de consolidado final",
        ],
    },
};

let sidebarOrionOriginal = null;
let monitorOrionOriginal = null;
let tituloMonitorOrionOriginal = null;

function obtenerSidebarPrincipal() {
    return document.getElementById("sidebar");
}

function obtenerMonitorCentral() {
    return document.getElementById("monitor-content");
}

function estaEnPaginaPrincipal() {
    const sidebar = obtenerSidebarPrincipal();
    const monitor = obtenerMonitorCentral();

    const rutaActual = window.location.pathname;
    const esRutaInicio =
        rutaActual === "/" ||
        rutaActual === "" ||
        rutaActual.endsWith("/index");

    return Boolean(sidebar && monitor && esRutaInicio);
}

function estaEnPaginaLogs() {
    const rutaActual = window.location.pathname.toLowerCase();

    return (
        rutaActual.includes("logs") ||
        rutaActual.includes("log")
    );
}

function actualizarLayoutPorPagina() {
    const sidebar = obtenerSidebarPrincipal();
    const mainLayout = document.querySelector(".main-layout");

    if (!sidebar) {
        return;
    }

    if (estaEnPaginaLogs()) {
        sidebar.style.display = "none";

        if (mainLayout) {
            mainLayout.classList.add("sin-sidebar");
        }

        return;
    }

    sidebar.style.display = "";

    if (mainLayout) {
        mainLayout.classList.remove("sin-sidebar");
    }
}


function obtenerTituloMonitor() {
    return (
        document.querySelector(".monitor-header h2") ||
        document.querySelector(".monitor h2")
    );
}

function guardarVistaOrionOriginal() {
    const sidebar = obtenerSidebarPrincipal();
    const monitor = obtenerMonitorCentral();
    const titulo = obtenerTituloMonitor();

    if (sidebar && sidebarOrionOriginal === null) {
        sidebarOrionOriginal = sidebar.innerHTML;
    }

    if (monitor && monitorOrionOriginal === null) {
        monitorOrionOriginal = monitor.innerHTML;
    }

    if (titulo && tituloMonitorOrionOriginal === null) {
        tituloMonitorOrionOriginal = titulo.textContent;
    }
}

function activarBotonModulo(moduloActivo) {
    Object.entries(MODULOS_UI).forEach(([modulo, config]) => {
        const boton = document.getElementById(config.botonId);

        if (boton) {
            boton.classList.toggle("active", modulo === moduloActivo);
        }
    });
}

function normalizarFechaAster(valor) {
    const limpio = String(valor || "").replace(/[^0-9]/g, "");

    if (limpio.length === 8) {
        return limpio;
    }

    return String(valor || "").trim();
}

function obtenerFechaProcesoAster() {
    return normalizarFechaAster(
        getInputValue("fechaInput") ||
        getInputValue("asterFechaProceso") ||
        getInputValue("asterFechaConsultaSql") ||
        getInputValue("asterFaseIFecha")
    );
}

function sincronizarFechaAster(valor) {
    const fecha = normalizarFechaAster(valor);

    [
        "fechaInput",
        "asterFechaProceso",
        "asterFechaConsultaSql",
        "asterFaseIFecha",
    ].forEach((id) => {
        const input = document.getElementById(id);

        if (input && "value" in input) {
            input.value = fecha;
        }
    });

    return fecha;
}


function construirSidebarAster(config) {
    const template = document.getElementById("tpl-sidebar-aster");

    if (!template) {
        return htmlError("No se encontró el template HTML del sidebar ASTER.");
    }

    return template.innerHTML;
}

function construirMonitorAster(config) {
    const template = document.getElementById("tpl-monitor-aster");

    if (!template) {
        return htmlError("No se encontró el template HTML del monitor ASTER.");
    }

    return template.innerHTML;
}

function construirSidebarTemporal(config) {
    const pasosHtml = config.pasos
        .map((paso) => `<li>${paso}</li>`)
        .join("");

    return `
        <div class="sidebar-columns modulo-placeholder-sidebar">
            <div class="sidebar-fases-col" style="width:100%; padding-left:0;">
                <details open>
                    <summary>${config.tituloSidebar}</summary>
                    <div class="fase-actions">
                        <div class="log-line info">
                            ⏳ Módulo en preparación.
                        </div>
                        <ul style="margin-left:16px; line-height:1.8; color:#ccc;">
                            ${pasosHtml}
                        </ul>
                    </div>
                </details>
            </div>
        </div>
    `;
}

function construirMonitorTemporal(config) {
    const pasosHtml = config.pasos
        .map((paso) => `<li>${paso}</li>`)
        .join("");

    return `
        <details class="panel-monitor" open>
            <summary>
                <span class="panel-icon">🧩</span>
                ${config.tituloMonitor}
            </summary>
            <div class="panel-body">
                <div class="log-line info">
                    ${config.descripcion}
                </div>

                <table class="dataframe" style="width:100%; margin-top:10px;">
                    <tr style="background:#1e3a5f; color:#fff;">
                        <th>Estado</th>
                        <th>Descripción</th>
                    </tr>
                    <tr>
                        <td><b>Temporal</b></td>
                        <td>La interfaz del módulo ya está separada visualmente.</td>
                    </tr>
                    <tr>
                        <td><b>Siguiente paso</b></td>
                        <td>Implementar sus fases reales cuando se defina el flujo operativo.</td>
                    </tr>
                </table>

                <div style="margin-top:12px;">
                    <b>Fases previstas:</b>
                    <ul style="margin-left:18px; margin-top:6px; line-height:1.8;">
                        ${pasosHtml}
                    </ul>
                </div>
            </div>
        </details>
    `;
}

function restaurarModuloOrion() {
    const sidebar = obtenerSidebarPrincipal();
    const monitor = obtenerMonitorCentral();
    const titulo = obtenerTituloMonitor();

    if (sidebar && sidebarOrionOriginal !== null) {
        sidebar.innerHTML = sidebarOrionOriginal;
    }

    if (monitor && monitorOrionOriginal !== null) {
        monitor.innerHTML = monitorOrionOriginal;
    }

    if (titulo) {
        titulo.textContent = tituloMonitorOrionOriginal || "Monitor de Ejecución";
    }
}

function mostrarModuloTemporal(modulo) {
    const config = MODULOS_UI[modulo];
    const sidebar = obtenerSidebarPrincipal();
    const monitor = obtenerMonitorCentral();
    const titulo = obtenerTituloMonitor();

    if (!config || modulo === "orion") {
        restaurarModuloOrion();
        return;
    }

    if (modulo === "aister") {
        if (sidebar) {
            sidebar.innerHTML = construirSidebarAster(config);
        }

        if (monitor) {
            monitor.innerHTML = construirMonitorAster(config);

            if (
                typeof obtenerFechaProcesoAster === "function" &&
                typeof sincronizarFechaAster === "function"
            ) {
                sincronizarFechaAster(obtenerFechaProcesoAster());
            }
        }

        if (titulo) {
            titulo.textContent = config.tituloMonitor;
        }

        return;
    }

    if (sidebar) {
        sidebar.innerHTML = construirSidebarTemporal(config);
    }

    if (monitor) {
        monitor.innerHTML = construirMonitorTemporal(config);
    }

    if (titulo) {
        titulo.textContent = config.tituloMonitor;
    }
}


function seleccionarModulo(modulo) {
    const moduloNormalizado = MODULOS_UI[modulo] ? modulo : "orion";

    localStorage.setItem("moduloActivoOrionDiario", moduloNormalizado);

    if (!estaEnPaginaPrincipal()) {
        window.location.href = "/";
        return;
    }

    actualizarLayoutPorPagina();
    guardarVistaOrionOriginal();

    if (moduloNormalizado === "orion") {
        restaurarModuloOrion();
    } else {
        mostrarModuloTemporal(moduloNormalizado);
    }

    activarBotonModulo(moduloNormalizado);
}

document.addEventListener("DOMContentLoaded", () => {
    actualizarLayoutPorPagina();
    guardarVistaOrionOriginal();

    const moduloGuardado =
        localStorage.getItem("moduloActivoOrionDiario") || "orion";

    if (estaEnPaginaPrincipal()) {
        seleccionarModulo(moduloGuardado);
    } else {
        activarBotonModulo(moduloGuardado);
    }
});

/* ---------- EXPOSICIÓN GLOBAL PARA ONCLICK EN TEMPLATES ---------- */
window.seleccionarModulo = seleccionarModulo;
window.normalizar = normalizar;
window.insertarEnPanel = insertarEnPanel;
window.actualizarTotalesHeader = actualizarTotalesHeader;
window.cerrarOtrosDetails = cerrarOtrosDetails;
window.marcarPasoCompletado = marcarPasoCompletado;
window.toggleSidebar = toggleSidebar;
window.ejecutarAccion = ejecutarAccion;
window.copiarDistribucionSeleccionada = copiarDistribucionSeleccionada;
window.actualizarCuadre = actualizarCuadre;
window.subirOCR = subirOCR;
window.consolidarTotales = consolidarTotales;
window.probarConexion = probarConexion;
window.seleccionarConexion = seleccionarConexion;
window.actualizarBadgesConexion = actualizarBadgesConexion;
window.resetTodo = resetTodo;
window.insertarDatos = insertarDatos;
window.verificarCarga = verificarCarga;
window.abrirConsolidado = abrirConsolidado;
window.seleccionarConexionConsolidado = seleccionarConexionConsolidado;
window.ejecutarConsultaConsolidado = ejecutarConsultaConsolidado;
window.aplicarFiltroYExportar = aplicarFiltroYExportar;
window.normalizarFechaAster = normalizarFechaAster;
window.obtenerFechaProcesoAster = obtenerFechaProcesoAster;
window.sincronizarFechaAster = sincronizarFechaAster;


