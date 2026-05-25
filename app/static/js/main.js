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

/* ---------- OCR ---------- */

/* ---------- CONEXIONES Y CARGA A SQL SERVER ---------- */

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
let moduloActivoActual = "orion";
const vistasModuloCache = {};

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

function idsEstadoFormularioPersistente() {
    return [
        "fechaInput",
        "manualOrion",
        "manualAister",
        "manualTotalAster",
        "asterFechaProceso",
        "asterRutaBase",
        "asterFechaConsultaSql",
        "asterConexionInsercion",
        "asterHistorialLimite",
        "asterFaseIConexion",
        "asterFaseIFecha",
        "consFecha",
        "consMeses",
        "cons-temp-id",
    ];
}

function claveEstadoInput(id) {
    return `orionDiario.ui.${id}`;
}

function persistirEstadoInputsVisibles() {
    idsEstadoFormularioPersistente().forEach((id) => {
        const elemento = document.getElementById(id);

        if (!elemento || !("value" in elemento)) {
            return;
        }

        localStorage.setItem(claveEstadoInput(id), elemento.value || "");
    });
}

function restaurarEstadoInputsVisibles() {
    idsEstadoFormularioPersistente().forEach((id) => {
        const elemento = document.getElementById(id);

        if (!elemento || !("value" in elemento)) {
            return;
        }

        const valor = localStorage.getItem(claveEstadoInput(id));

        if (valor !== null) {
            elemento.value = valor;
        }
    });
}

function serializarValoresDeFormulario(contenedor) {
    if (!contenedor) {
        return;
    }

    contenedor.querySelectorAll("input, textarea, select").forEach((elemento) => {
        if (elemento.tagName === "SELECT") {
            Array.from(elemento.options).forEach((option) => {
                option.removeAttribute("selected");

                if (option.value === elemento.value) {
                    option.setAttribute("selected", "selected");
                }
            });

            return;
        }

        if (elemento.type === "checkbox" || elemento.type === "radio") {
            if (elemento.checked) {
                elemento.setAttribute("checked", "checked");
            } else {
                elemento.removeAttribute("checked");
            }

            return;
        }

        if (elemento.tagName === "TEXTAREA") {
            elemento.textContent = elemento.value || "";
            return;
        }

        if ("value" in elemento) {
            elemento.setAttribute("value", elemento.value || "");
        }
    });
}

function guardarVistaModuloActual() {
    if (!estaEnPaginaPrincipal()) {
        return;
    }

    const sidebar = obtenerSidebarPrincipal();
    const monitor = obtenerMonitorCentral();
    const titulo = obtenerTituloMonitor();

    if (!sidebar || !monitor) {
        return;
    }

    persistirEstadoInputsVisibles();

    serializarValoresDeFormulario(sidebar);
    serializarValoresDeFormulario(monitor);

    vistasModuloCache[moduloActivoActual] = {
        sidebarHtml: sidebar.innerHTML,
        monitorHtml: monitor.innerHTML,
        titulo: titulo ? titulo.textContent : "",
    };
}

function restaurarVistaModuloCache(modulo) {
    const vista = vistasModuloCache[modulo];

    if (!vista) {
        return false;
    }

    const sidebar = obtenerSidebarPrincipal();
    const monitor = obtenerMonitorCentral();
    const titulo = obtenerTituloMonitor();

    if (sidebar) {
        sidebar.innerHTML = vista.sidebarHtml;
    }

    if (monitor) {
        monitor.innerHTML = vista.monitorHtml;
    }

    if (titulo && vista.titulo) {
        titulo.textContent = vista.titulo;
    }

    restaurarEstadoInputsVisibles();

    if (
        modulo === "aister" &&
        typeof window.obtenerFechaProcesoAster === "function" &&
        typeof window.sincronizarFechaAster === "function"
    ) {
        window.sincronizarFechaAster(window.obtenerFechaProcesoAster());
    }

    return true;
}

function registrarPersistenciaInputsDinamicos() {
    if (window.__orionPersistenciaInputsActiva) {
        return;
    }

    window.__orionPersistenciaInputsActiva = true;

    const guardar = (event) => {
        const target = event.target;

        if (!target || !target.id) {
            return;
        }

        if (!idsEstadoFormularioPersistente().includes(target.id)) {
            return;
        }

        if ("value" in target) {
            localStorage.setItem(claveEstadoInput(target.id), target.value || "");
        }

        const idsFechaAster = [
            "fechaInput",
            "asterFechaProceso",
            "asterFechaConsultaSql",
            "asterFaseIFecha",
        ];

        if (
            idsFechaAster.includes(target.id) &&
            typeof window.sincronizarFechaAster === "function"
        ) {
            window.sincronizarFechaAster(target.value || "");
            persistirEstadoInputsVisibles();
        }
    };

    document.addEventListener("input", guardar);
    document.addEventListener("change", guardar);
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
    guardarVistaModuloActual();

    if (moduloNormalizado === "orion") {
        if (!restaurarVistaModuloCache("orion")) {
            restaurarModuloOrion();
            restaurarEstadoInputsVisibles();
        }
    } else {
        if (!restaurarVistaModuloCache(moduloNormalizado)) {
            mostrarModuloTemporal(moduloNormalizado);
            restaurarEstadoInputsVisibles();
        }
    }

    moduloActivoActual = moduloNormalizado;

    if (
        moduloNormalizado === "aister" &&
        typeof window.obtenerFechaProcesoAster === "function" &&
        typeof window.sincronizarFechaAster === "function"
    ) {
        window.sincronizarFechaAster(window.obtenerFechaProcesoAster());
        persistirEstadoInputsVisibles();
    }

    activarBotonModulo(moduloNormalizado);
}

document.addEventListener("DOMContentLoaded", () => {
    registrarPersistenciaInputsDinamicos();
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
window.getById = getById;
window.htmlLoading = htmlLoading;
window.htmlError = htmlError;
window.esRespuestaExitosa = esRespuestaExitosa;
window.getInputValue = getInputValue;
window.fetchTexto = fetchTexto;
window.postFormTexto = postFormTexto;
window.normalizarFechaOrion = normalizarFechaOrion;
window.seleccionarModulo = seleccionarModulo;
window.normalizar = normalizar;
window.insertarEnPanel = insertarEnPanel;
window.actualizarTotalesHeader = actualizarTotalesHeader;
window.cerrarOtrosDetails = cerrarOtrosDetails;
window.marcarPasoCompletado = marcarPasoCompletado;
window.toggleSidebar = toggleSidebar;
window.guardarVistaModuloActual = guardarVistaModuloActual;
window.restaurarVistaModuloCache = restaurarVistaModuloCache;
window.resetTodo = resetTodo;
window.normalizarFechaAster = normalizarFechaAster;
window.obtenerFechaProcesoAster = obtenerFechaProcesoAster;
window.sincronizarFechaAster = sincronizarFechaAster;


