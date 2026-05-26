/* ============================================================
   ORION WORKFLOW ENGINE V1
   Fuente de verdad explícita para acciones ORION.
   No depende de MutationObserver ni de leer todo el HTML.
   ============================================================ */

(function () {
    "use strict";

    const STATE_KEY_PREFIX = "orionDiario.workflow.orion.v1";

    const ACTIONS = {
        "crear.carpetas": {
            phase: "A",
            label: "Crear Carpetas",
            panelId: "panel-crear-carpetas",
            wrapperId: "panel-crear-carpetas-wrapper",
            buttonId: "btn-wf-crear-carpetas",
            method: "GET",
            endpoint: "/accion/crear-carpetas",
        },
        "verificar.red": {
            phase: "B",
            label: "Verificar Red",
            panelId: "panel-verificar-red",
            wrapperId: "panel-verificar-red-wrapper",
            buttonId: "btn-wf-verificar-red",
            method: "GET",
            endpoint: "/accion/verificar-red",
        },
        "distribuir.preparar": {
            phase: "D",
            label: "Preparar distribución",
            panelId: "panel-distribuir",
            wrapperId: "panel-distribuir-wrapper",
            buttonId: "btn-panel-distribuir",
            method: "GET",
            endpoint: "/accion/distribuir",
        },
        "distribuir.copiar": {
            phase: "D",
            label: "Copiar seleccionados",
            panelId: "panel-distribuir",
            wrapperId: "panel-distribuir-wrapper",
            buttonId: "btn-copiar-distribucion-orion",
            method: "POST_JSON",
            endpoint: "/accion/distribuir-seleccionados",
        },

        "procesar.discador": {
            phase: "F",
            label: "Procesar Discador",
            panelId: "panel-discador",
            wrapperId: "panel-discador-wrapper",
            buttonId: "",
            method: "GET",
            endpoint: "/accion/procesar-discador",
        },
        "procesar.causales": {
            phase: "F",
            label: "Procesar Causales",
            panelId: "panel-causales",
            wrapperId: "panel-causales-wrapper",
            buttonId: "",
            method: "GET",
            endpoint: "/accion/procesar-causales",
        },
        "procesar.lotes": {
            phase: "F",
            label: "Procesar Lotes",
            panelId: "panel-lotes",
            wrapperId: "panel-lotes-wrapper",
            buttonId: "",
            method: "GET",
            endpoint: "/accion/procesar-lotes",
        },
        "procesar.comparar": {
            phase: "F",
            label: "Comparar Lotes",
            panelId: "panel-comparar",
            wrapperId: "panel-comparar-wrapper",
            buttonId: "",
            method: "GET",
            endpoint: "/accion/comparar-lotes",
        },

        "carga.causales.verificar": {
            phase: "G",
            tipo: "causales",
            label: "Verificar Causales",
            panelId: "panel-carga-causales",
            wrapperId: "panel-carga-causales-wrapper",
            buttonId: "btn-wf-verificar-causales",
            method: "POST_FORM",
            endpoint: "/accion/verificar-carga",
        },
        "carga.causales.insertar": {
            phase: "G",
            tipo: "causales",
            label: "Insertar Causales",
            panelId: "panel-carga-causales",
            wrapperId: "panel-carga-causales-wrapper",
            buttonId: "btn-wf-insertar-causales",
            method: "POST_FORM",
            endpoint: "/accion/insertar-datos",
            confirmRemote: true,
        },

        "carga.lotes.verificar": {
            phase: "G",
            tipo: "lote",
            label: "Verificar Lotes",
            panelId: "panel-carga-lote",
            wrapperId: "panel-carga-lote-wrapper",
            buttonId: "btn-wf-verificar-lotes",
            method: "POST_FORM",
            endpoint: "/accion/verificar-carga",
        },
        "carga.lotes.insertar": {
            phase: "G",
            tipo: "lote",
            label: "Insertar Lotes",
            panelId: "panel-carga-lote",
            wrapperId: "panel-carga-lote-wrapper",
            buttonId: "btn-wf-insertar-lotes",
            method: "POST_FORM",
            endpoint: "/accion/insertar-datos",
            confirmRemote: true,
        },

        "carga.discador.verificar": {
            phase: "G",
            tipo: "discador",
            label: "Verificar Discador",
            panelId: "panel-carga-discador",
            wrapperId: "panel-carga-discador-wrapper",
            buttonId: "btn-wf-verificar-discador",
            method: "POST_FORM",
            endpoint: "/accion/verificar-carga",
        },
        "carga.discador.insertar": {
            phase: "G",
            tipo: "discador",
            label: "Insertar Discador",
            panelId: "panel-carga-discador",
            wrapperId: "panel-carga-discador-wrapper",
            buttonId: "btn-wf-insertar-discador",
            method: "POST_FORM",
            endpoint: "/accion/insertar-datos",
            confirmRemote: true,
        },
    };

    function byId(id) {
        return document.getElementById(id);
    }

    function getFechaOrionWorkflow() {
        const candidatos = [
            "fechaInputPanelCrear",
            "fechaInput",
            "fechaProceso",
        ];

        for (const id of candidatos) {
            const el = byId(id);

            if (el && String(el.value || "").trim()) {
                return String(el.value || "").trim();
            }
        }

        return "";
    }

    function normalizarFechaWorkflow(valor) {
        const v = String(valor || "").trim();

        if (!v) {
            return "";
        }

        if (typeof window.normalizarFechaOrion === "function") {
            return window.normalizarFechaOrion(v);
        }

        return v;
    }

    function htmlLoadingWorkflow(texto) {
        if (typeof window.htmlLoading === "function") {
            return window.htmlLoading(texto);
        }

        return `<div class="log-line info">⏳ ${texto}</div>`;
    }

    function htmlErrorWorkflow(texto) {
        if (typeof window.htmlError === "function") {
            return window.htmlError(texto);
        }

        return `<div class="log-line error">❌ ${texto}</div>`;
    }

    function esRespuestaExitosaWorkflow(html) {
        const texto = String(html || "").toLowerCase();

        if (
            texto.includes("traceback") ||
            texto.includes("not found") ||
            texto.includes("http 500") ||
            texto.includes("error copiando") ||
            texto.includes("❌")
        ) {
            return false;
        }

        if (typeof window.esRespuestaExitosa === "function") {
            return window.esRespuestaExitosa(html);
        }

        return true;
    }


    function getWorkflowStateKey() {
        const fecha = normalizarFechaWorkflow(getFechaOrionWorkflow());

        if (!fecha) {
            return `${STATE_KEY_PREFIX}.sin_fecha`;
        }

        return `${STATE_KEY_PREFIX}.${fecha}`;
    }

    function limpiarEstadoWorkflowLegacyGlobal() {
        // Limpia el estado global anterior para que no pinte D como completado en fechas nuevas.
        localStorage.removeItem("orionDiario.workflow.orion.v1");
    }

    function leerEstado() {
        try {
            return JSON.parse(localStorage.getItem(getWorkflowStateKey()) || "{}");
        } catch {
            return {};
        }
    }



    function guardarEstado(estado) {
        localStorage.setItem(getWorkflowStateKey(), JSON.stringify(estado));
    }



    function setEstado(actionName, status, detail) {
        const action = ACTIONS[actionName];

        if (!action) {
            return;
        }

        const estado = leerEstado();

        estado[actionName] = {
            status,
            detail: detail || "",
            updatedAt: new Date().toLocaleTimeString(),
        };

        guardarEstado(estado);
        renderEstadoWorkflow(actionName);
        actualizarEstadoWorkflowDirecto(action.phase);
    }





    function estadoMeta(status) {
        const data = {
            pending: ["⚪", "Pendiente", "pending"],
            running: ["⚙️", "Ejecutando", "running"],
            ready: ["ℹ️", "Listo", "info"],
            done: ["✅", "Completado", "done"],
            error: ["❌", "Error", "error"],
        };

        return data[status] || data.pending;
    }


function limpiarChipsViejosFaseD() {
        const wrapper = byId("panel-distribuir-wrapper");

        if (!wrapper) {
            return;
        }

        wrapper.querySelectorAll(".orion-phase-header-chip").forEach((chip) => {
            chip.remove();
        });
    }

    function actualizarEstadoFaseDDirecto() {
        limpiarChipsViejosFaseD();

        const estado = calcularEstadoDistribuir();
        const [icon, label, cls] = estadoMeta(estado.status);

        const legacyStatus = estado.status === "ready" ? "info" : estado.status;
        const legacyLabel = estado.status === "ready" ? "Revisar" : label;

        // Persistir D en el tracker viejo, pero calculado desde la fecha actual.
        try {
            const key = "orionDiario.ui.orion.phaseStatus";
            const raw = localStorage.getItem(key);
            const phaseStatus = raw ? JSON.parse(raw) : {};

            phaseStatus.D = {
                status: legacyStatus,
                detail: estado.detail || legacyLabel,
                updatedAt: new Date().toLocaleTimeString(),
            };

            localStorage.setItem(key, JSON.stringify(phaseStatus));
        } catch {
            // No bloquear UI por fallo de localStorage.
        }

        const sidebarItem = document.querySelector('[data-orion-phase="D"]');

        if (sidebarItem) {
            sidebarItem.classList.remove("pending", "running", "done", "error", "info");
            sidebarItem.classList.add(cls);

            const state = sidebarItem.querySelector(".orion-phase-state");

            if (state) {
                state.textContent = `${icon} ${legacyLabel}`;
            }
        }

        const globalChip = byId("wf-status-distribuir-global");

        if (globalChip) {
            globalChip.className = `wf-status-chip ${cls}`;
            globalChip.textContent = `${icon} ${legacyLabel}`;
            globalChip.title = estado.detail || legacyLabel;
        }

        setTimeout(limpiarChipsViejosFaseD, 50);
        setTimeout(limpiarChipsViejosFaseD, 300);
    }








    function calcularEstadoProcesamiento() {
        const estado = leerEstado();

        const acciones = [
            "procesar.discador",
            "procesar.causales",
            "procesar.lotes",
            "procesar.comparar",
        ];

        const estados = acciones.map((accion) => estado[accion]?.status || "pending");

        if (estados.includes("running")) {
            return { status: "running", detail: "Procesamiento en ejecución" };
        }

        if (estados.includes("error")) {
            return { status: "error", detail: "Error en procesamiento" };
        }

        if (estados.every((item) => item === "done")) {
            return { status: "done", detail: "Procesamiento completado" };
        }

        if (estados.some((item) => item === "done")) {
            return { status: "ready", detail: "Procesamiento parcial" };
        }

        return { status: "pending", detail: "Procesamiento pendiente" };
    }

    function actualizarEstadoFaseFDirecto() {
        const estado = calcularEstadoProcesamiento();
        const [icon, label, cls] = estadoMeta(estado.status);

        const legacyStatus = estado.status === "ready" ? "info" : estado.status;
        const legacyLabel = estado.status === "ready" ? "Revisar" : label;

        try {
            const key = "orionDiario.ui.orion.phaseStatus";
            const raw = localStorage.getItem(key);
            const phaseStatus = raw ? JSON.parse(raw) : {};

            phaseStatus.F = {
                status: legacyStatus,
                detail: estado.detail || legacyLabel,
                updatedAt: new Date().toLocaleTimeString(),
            };

            localStorage.setItem(key, JSON.stringify(phaseStatus));
        } catch {
            // No bloquear UI por fallo de localStorage.
        }

        const sidebarItem = document.querySelector('[data-orion-phase="F"]');

        if (sidebarItem) {
            sidebarItem.classList.remove("pending", "running", "done", "error", "info");
            sidebarItem.classList.add(cls);

            const state = sidebarItem.querySelector(".orion-phase-state");

            if (state) {
                state.textContent = `${icon} ${legacyLabel}`;
            }
        }
    }

    function actualizarEstadoWorkflowDirecto(phase) {
        if (phase === "A") {
            actualizarEstadoFaseSimpleDirecto("A", "crear.carpetas");
            return;
        }

        if (phase === "B") {
            actualizarEstadoFaseSimpleDirecto("B", "verificar.red");
            return;
        }

        if (phase === "D") {
            actualizarEstadoFaseDDirecto();
            return;
        }

        if (phase === "F") {
            actualizarEstadoFaseFDirecto();
            return;
        }

        if (phase === "G") {
            actualizarEstadoFaseGDirecto();
            return;
        }
    }






    function tipoKeyCargaWorkflow(tipo) {
        if (tipo === "lote") {
            return "lotes";
        }

        return tipo;
    }

    function getConexionCargaWorkflow(tipo) {
        const key = tipoKeyCargaWorkflow(tipo);
        const select = byId(`wf-conexion-${key}`);

        if (select && select.value) {
            return select.value;
        }

        return "local";
    }

    function crearFormDataCargaWorkflow(actionName, fecha) {
        const action = ACTIONS[actionName];
        const formData = new FormData();

        formData.append("tipo", action.tipo || "");
        formData.append("conexion", getConexionCargaWorkflow(action.tipo));
        formData.append("fecha", fecha);

        return formData;
    }

    async function ejecutarPostForm(actionName, fecha) {
        const action = ACTIONS[actionName];
        const conexion = getConexionCargaWorkflow(action.tipo);

        if (action.confirmRemote && conexion === "remoto") {
            const confirmar = confirm(
                "Está a punto de insertar en REMOTO/Producción. ¿Desea continuar?"
            );

            if (!confirmar) {
                throw new Error("Operación cancelada por el usuario.");
            }
        }

        const response = await fetch(`${action.endpoint}?_=${Date.now()}`, {
            method: "POST",
            cache: "no-store",
            body: crearFormDataCargaWorkflow(actionName, fecha),
            headers: {
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return response.text();
    }

    function estadoCargaTipoWorkflow(tipo) {
        const key = tipoKeyCargaWorkflow(tipo);
        const estado = leerEstado();

        const verificar = estado[`carga.${key}.verificar`]?.status || "pending";
        const insertar = estado[`carga.${key}.insertar`]?.status || "pending";

        if (verificar === "running" || insertar === "running") {
            return { status: "running", detail: "Carga en ejecución" };
        }

        if (verificar === "error" || insertar === "error") {
            return { status: "error", detail: "Error en carga" };
        }

        if (insertar === "done") {
            return { status: "done", detail: "Carga completada" };
        }

        if (verificar === "done") {
            return { status: "ready", detail: "Consolidado verificado" };
        }

        return { status: "pending", detail: "Carga pendiente" };
    }

    function calcularEstadoCargaGlobal() {
        const estados = [
            estadoCargaTipoWorkflow("causales").status,
            estadoCargaTipoWorkflow("lote").status,
            estadoCargaTipoWorkflow("discador").status,
        ];

        if (estados.includes("running")) {
            return { status: "running", detail: "Carga consolidada en ejecución" };
        }

        if (estados.includes("error")) {
            return { status: "error", detail: "Error en carga consolidada" };
        }

        if (estados.every((item) => item === "done")) {
            return { status: "done", detail: "Cargas consolidadas completadas" };
        }

        if (estados.some((item) => item === "done" || item === "ready")) {
            return { status: "ready", detail: "Carga consolidada parcial" };
        }

        return { status: "pending", detail: "Carga consolidada pendiente" };
    }

    function actualizarEstadoCargaTipoDirecto(tipo) {
        const key = tipoKeyCargaWorkflow(tipo);
        const estado = estadoCargaTipoWorkflow(tipo);
        const [icon, label, cls] = estadoMeta(estado.status);

        const legacyLabel = estado.status === "ready" ? "Revisar" : label;

        const chip = byId(`wf-status-carga-${key}-global`);

        if (chip) {
            chip.className = `wf-status-chip ${cls}`;
            chip.textContent = `${icon} ${legacyLabel}`;
            chip.title = estado.detail || legacyLabel;
        }
    }

    function actualizarEstadoFaseGDirecto() {
        ["causales", "lote", "discador"].forEach(actualizarEstadoCargaTipoDirecto);

        const estado = calcularEstadoCargaGlobal();
        const [icon, label, cls] = estadoMeta(estado.status);

        const legacyStatus = estado.status === "ready" ? "info" : estado.status;
        const legacyLabel = estado.status === "ready" ? "Revisar" : label;

        try {
            const key = "orionDiario.ui.orion.phaseStatus";
            const raw = localStorage.getItem(key);
            const phaseStatus = raw ? JSON.parse(raw) : {};

            phaseStatus.G = {
                status: legacyStatus,
                detail: estado.detail || legacyLabel,
                updatedAt: new Date().toLocaleTimeString(),
            };

            localStorage.setItem(key, JSON.stringify(phaseStatus));
        } catch {
            // No bloquear UI por fallo de localStorage.
        }

        const sidebarItem = document.querySelector('[data-orion-phase="G"]');

        if (sidebarItem) {
            sidebarItem.classList.remove("pending", "running", "done", "error", "info");
            sidebarItem.classList.add(cls);

            const state = sidebarItem.querySelector(".orion-phase-state");

            if (state) {
                state.textContent = `${icon} ${legacyLabel}`;
            }
        }
    }


    function calcularEstadoSimpleWorkflow(actionName) {
        const estado = leerEstado();
        return estado[actionName]?.status || "pending";
    }

    function actualizarEstadoFaseSimpleDirecto(phase, actionName) {
        const status = calcularEstadoSimpleWorkflow(actionName);
        const [icon, label, cls] = estadoMeta(status);

        try {
            const key = "orionDiario.ui.orion.phaseStatus";
            const raw = localStorage.getItem(key);
            const phaseStatus = raw ? JSON.parse(raw) : {};

            phaseStatus[phase] = {
                status,
                detail: label,
                updatedAt: new Date().toLocaleTimeString(),
            };

            localStorage.setItem(key, JSON.stringify(phaseStatus));
        } catch {
            // No bloquear UI.
        }

        const sidebarItem = document.querySelector(`[data-orion-phase="${phase}"]`);

        if (sidebarItem) {
            sidebarItem.classList.remove("pending", "running", "done", "error", "info");
            sidebarItem.classList.add(cls);

            const state = sidebarItem.querySelector(".orion-phase-state");

            if (state) {
                state.textContent = `${icon} ${label}`;
            }
        }
    }

    function renderEstadoWorkflow(actionName) {
        const action = ACTIONS[actionName];

        if (!action) {
            return;
        }

        const estado = leerEstado();
        const item = estado[actionName] || { status: "pending", detail: "Pendiente" };
        const [icon, label, cls] = estadoMeta(item.status);

        const chip = byId(`wf-status-${actionName.replace(".", "-")}`);

        if (chip) {
            chip.className = `wf-status-chip ${cls}`;
            chip.textContent = `${icon} ${label}`;
            chip.title = item.detail || label;
        }

        const wrapper = byId(action.wrapperId);
        const summaryChip = wrapper?.querySelector(".orion-phase-header-chip");

        if (summaryChip && actionName.startsWith("distribuir.")) {
            const estadoDistribuir = calcularEstadoDistribuir();
            const [sIcon, sLabel, sCls] = estadoMeta(estadoDistribuir.status);

            summaryChip.className = `orion-phase-header-chip ${sCls}`;
            summaryChip.textContent = `${sIcon} ${sLabel}`;
            summaryChip.title = estadoDistribuir.detail;
        }
    }

    function calcularEstadoDistribuir() {
        const estado = leerEstado();
        const preparar = estado["distribuir.preparar"]?.status || "pending";
        const copiar = estado["distribuir.copiar"]?.status || "pending";

        if (preparar === "running" || copiar === "running") {
            return { status: "running", detail: "Distribución en ejecución" };
        }

        if (preparar === "error" || copiar === "error") {
            return { status: "error", detail: "Error en distribución" };
        }

        if (preparar === "done" && copiar === "done") {
            return { status: "done", detail: "Distribución completada" };
        }

        if (preparar === "done") {
            return { status: "ready", detail: "Archivos listos para copiar" };
        }

        return { status: "pending", detail: "Distribución pendiente" };
    }



    function abrirPanel(actionName) {
        const action = ACTIONS[actionName];

        if (!action) {
            return;
        }

        const wrapper = byId(action.wrapperId);

        if (!wrapper) {
            return;
        }

        if (wrapper.tagName.toLowerCase() === "details") {
            wrapper.open = true;
        }

        wrapper.classList.remove("orion-panel-focus-flash");
        void wrapper.offsetWidth;
        wrapper.classList.add("orion-panel-focus-flash");

        setTimeout(() => {
            wrapper.scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
        }, 80);
    }

    function setButtonBusy(actionName, busy) {
        const action = ACTIONS[actionName];
        const btn = byId(action?.buttonId || "");

        if (!btn) {
            return;
        }

        btn.disabled = Boolean(busy);
        btn.classList.toggle("is-busy", Boolean(busy));
    }

    function panel(actionName) {
        const action = ACTIONS[actionName];
        return byId(action?.panelId || "");
    }

    function obtenerSeleccionadosDistribucion() {
        const root = byId("panel-distribuir") || document;

        const checks = Array.from(
            root.querySelectorAll("input[type='checkbox']:checked")
        );

        return checks
            .map((check) => {
                const row = check.closest("tr");
                const categoria =
                    check.dataset.categoria ||
                    row?.dataset?.categoria ||
                    check.getAttribute("data-categoria") ||
                    "";

                const archivo =
                    check.dataset.archivo ||
                    row?.dataset?.archivo ||
                    check.getAttribute("data-archivo") ||
                    check.value ||
                    "";

                return {
                    categoria: String(categoria || "").trim(),
                    archivo: String(archivo || "").trim(),
                };
            })
            .filter((item) => {
                return (
                    item.categoria &&
                    item.archivo &&
                    item.archivo.toLowerCase() !== "on"
                );
            });
    }



    function prepararBotonCopiarDistribucion() {
        const root = byId("panel-distribuir");

        if (!root) {
            return;
        }

        const botones = Array.from(root.querySelectorAll("button, input[type='button'], input[type='submit']"));

        const boton = botones.find((btn) => {
            const texto = String(btn.textContent || btn.value || "").toLowerCase();
            return texto.includes("copiar") && texto.includes("seleccion");
        });

        if (!boton) {
            return;
        }

        boton.id = "btn-copiar-distribucion-orion";
        boton.type = "button";
        boton.disabled = false;
        boton.classList.remove("is-busy");

        boton.onclick = function (event) {
            event.preventDefault();
            event.stopPropagation();
            window.ejecutarWorkflowOrion("distribuir.copiar", boton);
            return false;
        };
    }



    function buildUrlGet(actionName, fecha) {
        const action = ACTIONS[actionName];
        const sep = action.endpoint.includes("?") ? "&" : "?";

        return `${action.endpoint}${sep}fecha=${encodeURIComponent(fecha)}&_=${Date.now()}`;
    }

    async function ejecutarGet(actionName, fecha) {
        const action = ACTIONS[actionName];

        const response = await fetch(buildUrlGet(actionName, fecha), {
            method: "GET",
            cache: "no-store",
            headers: {
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return response.text();
    }

    async function ejecutarPostJson(actionName, payload) {
        const action = ACTIONS[actionName];

        const response = await fetch(`${action.endpoint}?_=${Date.now()}`, {
            method: "POST",
            cache: "no-store",
            headers: {
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return response.text();
    }

    async function ejecutarWorkflowOrion(actionName, boton = null) {
        const action = ACTIONS[actionName];

        if (!action) {
            console.warn("Workflow ORION no registrado:", actionName);
            return "";
        }

        abrirPanel(actionName);

        const fecha = normalizarFechaWorkflow(getFechaOrionWorkflow());

        if (!fecha) {
            alert("Ingrese una fecha válida antes de ejecutar.");
            return "";
        }

        const target = panel(actionName);

        setEstado(actionName, "running", action.label);
        setButtonBusy(actionName, true);

        let seleccionados = [];

        try {
            if (action.method === "POST_JSON") {
                seleccionados = obtenerSeleccionadosDistribucion();

                if (!seleccionados.length) {
                    throw new Error("Seleccione al menos un archivo para copiar.");
                }
            }

            if (target) {
                if (action.method === "GET" || action.method === "POST_FORM") {
                    target.innerHTML = htmlLoadingWorkflow(action.label);
                } else {
                    const aviso = document.createElement("div");
                    aviso.className = "log-line info";
                    aviso.textContent = "⏳ Copiando archivos seleccionados...";
                    target.prepend(aviso);
                }
            }

            let html = "";

            if (action.method === "GET") {
                html = await ejecutarGet(actionName, fecha);
            } else if (action.method === "POST_JSON") {
                html = await ejecutarPostJson(actionName, {
                    fecha,
                    seleccionados,
                });
            } else if (action.method === "POST_FORM") {
                html = await ejecutarPostForm(actionName, fecha);
            } else {
                throw new Error(`Método no soportado: ${action.method}`);
            }

            if (target) {
                target.innerHTML = html;
            }

            if (actionName === "distribuir.preparar") {
                prepararBotonCopiarDistribucion();
            }

            const ok = esRespuestaExitosaWorkflow(html);

            setEstado(
                actionName,
                ok ? "done" : "error",
                ok ? "Completado" : "Error"
            );

            if (typeof window.actualizarIconoBoton === "function" && boton) {
                window.actualizarIconoBoton(boton, ok);
            }

            return html;
        } catch (error) {
            const mensaje = String(error?.message || error);

            if (target) {
                if (action.method === "GET" || action.method === "POST_FORM") {
                    target.innerHTML = htmlErrorWorkflow(mensaje);
                } else {
                    const aviso = document.createElement("div");
                    aviso.className = "log-line error";
                    aviso.textContent = `❌ ${mensaje}`;
                    target.prepend(aviso);
                }
            }

            setEstado(actionName, "error", mensaje);

            if (typeof window.actualizarIconoBoton === "function" && boton) {
                window.actualizarIconoBoton(boton, false);
            }

            return "";
        } finally {
            setButtonBusy(actionName, false);
            prepararBotonCopiarDistribucion();
        }
    }





    function abrirWorkflowOrion(actionName) {
        abrirPanel(actionName);
        renderEstadoWorkflow(actionName);
    }


    function registrarDelegadoCopiarDistribucion() {
        if (window.__orionWorkflowCopyDelegated) {
            return;
        }

        window.__orionWorkflowCopyDelegated = true;

        document.addEventListener("click", (event) => {
            const boton = event.target?.closest?.("button, input[type='button'], input[type='submit']");

            if (!boton) {
                return;
            }

            const root = boton.closest("#panel-distribuir");

            if (!root) {
                return;
            }

            const texto = String(boton.textContent || boton.value || "").toLowerCase();

            if (!(texto.includes("copiar") && texto.includes("seleccion"))) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            window.ejecutarWorkflowOrion("distribuir.copiar", boton);
        }, true);
    }

    function inicializarWorkflowOrion() {
        limpiarEstadoWorkflowLegacyGlobal();
        limpiarChipsViejosFaseD();
        limpiarChipsViejosFaseD();
        Object.keys(ACTIONS).forEach(renderEstadoWorkflow);
        actualizarEstadoFaseDDirecto();
        actualizarEstadoFaseDDirecto();

        // Si el backend ya dejó el botón en HTML restaurado/cacheado, se normaliza.
        prepararBotonCopiarDistribucion();
        registrarDelegadoCopiarDistribucion();
        actualizarEstadoFaseDDirecto();
    }

    document.addEventListener("DOMContentLoaded", () => {
        setTimeout(inicializarWorkflowOrion, 100);
        setTimeout(inicializarWorkflowOrion, 600);
    });

    window.ejecutarWorkflowOrion = ejecutarWorkflowOrion;
    window.abrirWorkflowOrion = abrirWorkflowOrion;
    window.inicializarWorkflowOrion = inicializarWorkflowOrion;
    window.actualizarEstadoFaseSimpleDirecto = actualizarEstadoFaseSimpleDirecto;
    window.calcularEstadoSimpleWorkflow = calcularEstadoSimpleWorkflow;
    window.getConexionCargaWorkflow = getConexionCargaWorkflow;
    window.estadoCargaTipoWorkflow = estadoCargaTipoWorkflow;
    window.actualizarEstadoFaseGDirecto = actualizarEstadoFaseGDirecto;
    window.calcularEstadoCargaGlobal = calcularEstadoCargaGlobal;
    window.actualizarEstadoWorkflowDirecto = actualizarEstadoWorkflowDirecto;
    window.actualizarEstadoFaseFDirecto = actualizarEstadoFaseFDirecto;
    window.calcularEstadoProcesamiento = calcularEstadoProcesamiento;
    window.limpiarEstadoWorkflowLegacyGlobal = limpiarEstadoWorkflowLegacyGlobal;
    window.getWorkflowStateKey = getWorkflowStateKey;

    // Compatibilidad: si un HTML antiguo llama esta función, la redirigimos al workflow.
    window.copiarDistribucionSeleccionada = function (boton = null) {
        return ejecutarWorkflowOrion("distribuir.copiar", boton);
    };
})();
