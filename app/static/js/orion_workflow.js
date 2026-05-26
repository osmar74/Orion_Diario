/* ============================================================
   ORION WORKFLOW ENGINE V1
   Fuente de verdad explícita para acciones ORION.
   No depende de MutationObserver ni de leer todo el HTML.
   ============================================================ */

(function () {
    "use strict";

    const STATE_KEY_PREFIX = "orionDiario.workflow.orion.v1";

    const ACTIONS = {
        "consolidado.gestion.consultar": {
            phase: "G",
            label: "Consultar Consolidado Gestión Orion",
            panelId: "panel-consolidado-resultado",
            wrapperId: "panel-consolidado-wrapper",
            buttonId: "btn-wf-consolidado-consultar",
            method: "LEGACY_FUNCTION",
            legacyFunction: "ejecutarConsultaConsolidado",
        },
        "ocr.procesar": {
            phase: "C",
            label: "Procesar OCR",
            panelId: "ocr-result-content",
            wrapperId: "panel-ocr-wrapper",
            buttonId: "btn-wf-ocr-procesar",
            method: "LEGACY_FUNCTION",
            legacyFunction: "subirOCR",
        },
        "ocr.consolidar": {
            phase: "C",
            label: "Consolidar Totales",
            panelId: "ocr-consolidado-resultado",
            wrapperId: "panel-ocr-wrapper",
            buttonId: "btn-wf-consolidar-totales",
            method: "LEGACY_FUNCTION",
            legacyFunction: "consolidarTotales",
        },
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

        // Aceptar YYYY-MM-DD y convertir a YYYYMM_DD para endpoints ORION.
        const iso = v.match(/^(\d{4})-(\d{2})-(\d{2})$/);

        if (iso) {
            return `${iso[1]}${iso[2]}_${iso[3]}`;
        }

        // Aceptar YYYYMMDD y convertir a YYYYMM_DD.
        const ymd = v.match(/^(\d{4})(\d{2})(\d{2})$/);

        if (ymd) {
            return `${ymd[1]}${ymd[2]}_${ymd[3]}`;
        }

        // Aceptar YYYYMM_DD.
        if (/^\d{6}_\d{2}$/.test(v)) {
            return v;
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

        if (phase === "C") {
            actualizarEstadoFaseCDirecto();
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


    function estadoConsolidadoGestionWorkflow() {
        const estado = leerEstado();
        const consulta = estado["consolidado.gestion.consultar"]?.status || "pending";

        if (consulta === "running") {
            return { status: "running", detail: "Consulta consolidado en ejecución" };
        }

        if (consulta === "error") {
            return { status: "error", detail: "Error en consolidado gestión" };
        }

        if (consulta === "done") {
            return { status: "done", detail: "Consolidado gestión consultado" };
        }

        return { status: "pending", detail: "Consolidado gestión pendiente" };
    }

    function actualizarEstadoConsolidadoGestionDirecto() {
        const estado = estadoConsolidadoGestionWorkflow();
        const [icon, label, cls] = estadoMeta(estado.status);

        const legacyLabel = estado.status === "ready" ? "Revisar" : label;

        const chip = byId("wf-status-consolidado-gestion-global");

        if (chip) {
            chip.className = `wf-status-chip ${cls}`;
            chip.textContent = `${icon} ${legacyLabel}`;
            chip.title = estado.detail || legacyLabel;
        }
    }

    function calcularEstadoCargaGlobal() {
        const estados = [
            estadoCargaTipoWorkflow("causales").status,
            estadoCargaTipoWorkflow("lote").status,
            estadoCargaTipoWorkflow("discador").status,
            estadoConsolidadoGestionWorkflow().status,
        ];

        if (estados.includes("running")) {
            return { status: "running", detail: "Fase G en ejecución" };
        }

        if (estados.includes("error")) {
            return { status: "error", detail: "Error en Fase G" };
        }

        if (estados.every((item) => item === "done")) {
            return { status: "done", detail: "Fase G completada" };
        }

        if (estados.some((item) => item === "done" || item === "ready")) {
            return { status: "ready", detail: "Fase G parcial" };
        }

        return { status: "pending", detail: "Fase G pendiente" };
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
        actualizarEstadoConsolidadoGestionDirecto();

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


    const LEGACY_ORION_FUNCTIONS = {
        subirOCR:
            typeof window.subirOCR === "function"
                ? window.subirOCR.bind(window)
                : null,
        consolidarTotales:
            typeof window.consolidarTotales === "function"
                ? window.consolidarTotales.bind(window)
                : null,
        ejecutarConsultaConsolidado:
            typeof window.ejecutarConsultaConsolidado === "function"
                ? window.ejecutarConsultaConsolidado.bind(window)
                : null,
    };

    function mostrarModoOcrWorkflow() {
        const ocr = byId("orion-ocr-mode");
        const manual = byId("orion-manual-mode");
        const btnOcr = byId("btnModoOcrOrion");
        const btnManual = byId("btnModoManualOrion");

        if (ocr) {
            ocr.classList.add("active");
        }

        if (manual) {
            manual.classList.remove("active");
        }

        if (btnOcr) {
            btnOcr.classList.add("active");
        }

        if (btnManual) {
            btnManual.classList.remove("active");
        }
    }

    function mostrarModoManualWorkflow() {
        const ocr = byId("orion-ocr-mode");
        const manual = byId("orion-manual-mode");
        const btnOcr = byId("btnModoOcrOrion");
        const btnManual = byId("btnModoManualOrion");

        if (ocr) {
            ocr.classList.remove("active");
        }

        if (manual) {
            manual.classList.add("active");
        }

        if (btnOcr) {
            btnOcr.classList.remove("active");
        }

        if (btnManual) {
            btnManual.classList.add("active");
        }
    }

    function actualizarNombreArchivosOcrWorkflow() {
        const input = byId("ocrFiles");
        const resumen = byId("ocrFilesResumen");

        if (!input || !resumen) {
            return;
        }

        const total = input.files ? input.files.length : 0;

        if (!total) {
            resumen.textContent = "Ningún archivo seleccionado";
            return;
        }

        if (total === 1) {
            resumen.textContent = input.files[0].name;
            return;
        }

        resumen.textContent = `${total} archivos seleccionados`;
    }

    function validarTotalesWorkflow() {
        const orion = Number(byId("manualOrion")?.value || 0);
        const aister = Number(byId("manualAister")?.value || 0);

        return {
            orion,
            aister,
            valido: Number.isFinite(orion) && Number.isFinite(aister) && (orion > 0 || aister > 0),
        };
    }


    function getLegacyWorkflowFunction(nombre) {
        const fn = window[nombre];

        if (typeof fn === "function") {
            return fn.bind(window);
        }

        return null;
    }

    let CONEXION_CONSOLIDADO_WORKFLOW = "local";

    function seleccionarConexionConsolidadoWorkflow(tipo) {
        const normalizado = String(tipo || "local").toLowerCase() === "remoto"
            ? "remoto"
            : "local";

        CONEXION_CONSOLIDADO_WORKFLOW = normalizado;

        const btnLocal = byId("btn-wf-consolidado-local");
        const btnRemoto = byId("btn-wf-consolidado-remoto");
        const chip = byId("wf-status-consolidado-conexion");

        if (btnLocal) {
            btnLocal.classList.toggle("active", normalizado === "local");
        }

        if (btnRemoto) {
            btnRemoto.classList.toggle("active", normalizado === "remoto");
        }

        if (chip) {
            chip.className = normalizado === "local"
                ? "wf-status-chip done"
                : "wf-status-chip info";

            chip.textContent = normalizado === "local"
                ? "✅ Local activo"
                : "ℹ️ Remoto activo";

            chip.title = normalizado === "local"
                ? "Conexión local seleccionada"
                : "Conexión remota seleccionada";
        }

        if (typeof window.seleccionarConexionConsolidado === "function") {
            try {
                window.seleccionarConexionConsolidado(normalizado);
            } catch (error) {
                console.warn("No se pudo sincronizar conexión consolidado legacy:", error);
            }
        }
    }


    const CONSOLIDADO_RESULT_ALIAS_IDS = [
            "consolidado-body",
            "consolidado-resultado",
            "consolidadoContenido",
            "consolidadoResultado",
            "consultaConsolidadoResultado",
            "panel-consolidado-resultado",
            "panelConsolidadoResultado",
            "resultado-consolidado",
            "resultadoConsolidado",
            "resultadoConsultaConsolidado"
];

    function asegurarAliasesResultadoConsolidadoWorkflow() {
        const panel = byId("panel-consolidado-resultado");

        if (!panel) {
            return;
        }

        let root = byId("wf-consolidado-alias-root");

        if (!root) {
            root = document.createElement("div");
            root.id = "wf-consolidado-alias-root";
            root.className = "consolidado-alias-root";
            panel.appendChild(root);
        }

        CONSOLIDADO_RESULT_ALIAS_IDS.forEach((id) => {
            if (!id || id === "panel-consolidado-resultado") {
                return;
            }

            if (!document.getElementById(id)) {
                const alias = document.createElement("div");
                alias.id = id;
                alias.className = "consolidado-result-alias";
                root.appendChild(alias);
            }
        });
    }

    function inicializarConsolidadoWorkflow() {
        asegurarAliasesResultadoConsolidadoWorkflow();
        seleccionarConexionConsolidadoWorkflow(CONEXION_CONSOLIDADO_WORKFLOW);

        const fechaProceso = normalizarFechaWorkflow(getFechaOrionWorkflow());
        const consFecha = byId("consFecha");
        const consMeses = byId("consMeses");

        const limpia = fechaProceso.replace("_", "");

        if (fechaProceso && consFecha && !String(consFecha.value || "").trim()) {
            if (/^\d{8}$/.test(limpia)) {
                consFecha.value = `${limpia.slice(0, 4)}-${limpia.slice(4, 6)}-${limpia.slice(6, 8)}`;
            }
        }

        if (fechaProceso && consMeses && !String(consMeses.value || "").trim()) {
            if (/^\d{8}$/.test(limpia)) {
                consMeses.value = limpia.slice(0, 6);
            }
        }
    }





    function obtenerFechaConsolidadoWorkflow() {
        const consFecha = byId("consFecha");
        const consMeses = byId("consMeses");

        let fecha = String(consFecha?.value || "").trim();
        let meses = String(consMeses?.value || "").trim();

        const fechaProceso = normalizarFechaWorkflow(getFechaOrionWorkflow());
        const limpiaProceso = fechaProceso.replace("_", "");

        if (!fecha && /^\d{8}$/.test(limpiaProceso)) {
            fecha = `${limpiaProceso.slice(0, 4)}-${limpiaProceso.slice(4, 6)}-${limpiaProceso.slice(6, 8)}`;

            if (consFecha) {
                consFecha.value = fecha;
            }
        }

        if (!meses && /^\d{8}$/.test(limpiaProceso)) {
            meses = limpiaProceso.slice(0, 6);

            if (consMeses) {
                consMeses.value = meses;
            }
        }

        if (/^\d{8}$/.test(fecha)) {
            fecha = `${fecha.slice(0, 4)}-${fecha.slice(4, 6)}-${fecha.slice(6, 8)}`;

            if (consFecha) {
                consFecha.value = fecha;
            }
        }

        if (/^\d{6}_\d{2}$/.test(fecha)) {
            const limpia = fecha.replace("_", "");
            fecha = `${limpia.slice(0, 4)}-${limpia.slice(4, 6)}-${limpia.slice(6, 8)}`;

            if (consFecha) {
                consFecha.value = fecha;
            }
        }

        const fechaValida = /^\d{4}-\d{2}-\d{2}$/.test(fecha);
        const mesesValido = /^\d{6}$/.test(meses);

        return {
            fecha,
            meses,
            valido: fechaValida && mesesValido,
        };
    }

    async function ejecutarLegacyFunction(actionName, boton = null) {
        const action = ACTIONS[actionName];
        const fn = getLegacyWorkflowFunction(action.legacyFunction);

        if (typeof fn !== "function") {
            throw new Error(`No está disponible la función legacy ${action.legacyFunction}`);
        }

        if (actionName === "ocr.procesar") {
            const input = byId("ocrFiles");

            if (!input || !input.files || !input.files.length) {
                throw new Error("Seleccione al menos una imagen para procesar OCR.");
            }
        }

        if (actionName === "ocr.consolidar") {
            const totales = validarTotalesWorkflow();

            if (!totales.valido) {
                throw new Error("Ingrese totales válidos para Orion o Aister.");
            }
        }

        if (actionName === "consolidado.gestion.consultar") {
            inicializarConsolidadoWorkflow();
            asegurarAliasesResultadoConsolidadoWorkflow();
        }

        const resultado = fn(boton);

        if (resultado && typeof resultado.then === "function") {
            await resultado;
        } else {
            await new Promise((resolve) => setTimeout(resolve, 1200));
        }

        const target = panel(actionName);
        return target ? target.innerHTML : "OK";
    }



    function calcularEstadoOcrWorkflow() {
        const estado = leerEstado();

        const procesar = estado["ocr.procesar"]?.status || "pending";
        const consolidar = estado["ocr.consolidar"]?.status || "pending";

        if (procesar === "running" || consolidar === "running") {
            return { status: "running", detail: "OCR/Totales en ejecución" };
        }

        if (procesar === "error" || consolidar === "error") {
            return { status: "error", detail: "Error en OCR/Totales" };
        }

        if (consolidar === "done") {
            return { status: "done", detail: "Totales consolidados" };
        }

        if (procesar === "done") {
            return { status: "ready", detail: "OCR procesado, pendiente consolidar" };
        }

        return { status: "pending", detail: "OCR/Totales pendiente" };
    }

    function actualizarEstadoFaseCDirecto() {
        const estado = calcularEstadoOcrWorkflow();
        const [icon, label, cls] = estadoMeta(estado.status);

        const legacyStatus = estado.status === "ready" ? "info" : estado.status;
        const legacyLabel = estado.status === "ready" ? "Revisar" : label;

        try {
            const key = "orionDiario.ui.orion.phaseStatus";
            const raw = localStorage.getItem(key);
            const phaseStatus = raw ? JSON.parse(raw) : {};

            phaseStatus.C = {
                status: legacyStatus,
                detail: estado.detail || legacyLabel,
                updatedAt: new Date().toLocaleTimeString(),
            };

            localStorage.setItem(key, JSON.stringify(phaseStatus));
        } catch {
            // No bloquear UI.
        }

        const sidebarItem = document.querySelector('[data-orion-phase="C"]');

        if (sidebarItem) {
            sidebarItem.classList.remove("pending", "running", "done", "error", "info");
            sidebarItem.classList.add(cls);

            const state = sidebarItem.querySelector(".orion-phase-state");

            if (state) {
                state.textContent = `${icon} ${legacyLabel}`;
            }
        }

        const chip = byId("wf-status-ocr-global");

        if (chip) {
            chip.className = `wf-status-chip ${cls}`;
            chip.textContent = `${icon} ${legacyLabel}`;
            chip.title = estado.detail || legacyLabel;
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

        let fecha = normalizarFechaWorkflow(getFechaOrionWorkflow());

        if (actionName === "consolidado.gestion.consultar") {
            inicializarConsolidadoWorkflow();

            const params = obtenerFechaConsolidadoWorkflow();

            if (!params.valido) {
                alert("Ingrese una fecha válida y un mes de gestión válido para el consolidado.");
                return "";
            }

            // Para esta acción, la función legacy usa consFecha y consMeses.
            // Solo damos un valor interno para no bloquear el workflow.
            fecha = normalizarFechaWorkflow(params.fecha);
        }

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
                if (
                    action.method === "GET" ||
                    action.method === "POST_FORM"
                ) {
                    target.innerHTML = htmlLoadingWorkflow(action.label);
                } else if (action.method === "LEGACY_FUNCTION") {
                    // No borrar el panel antes de OCR/consolidación; la función legacy escribe su propio resultado.
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
            } else if (action.method === "LEGACY_FUNCTION") {
                html = await ejecutarLegacyFunction(actionName, boton);
            } else {
                throw new Error(`Método no soportado: ${action.method}`);
            }

            if (target && action.method !== "LEGACY_FUNCTION") {
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
                if (
                    action.method === "GET" ||
                    action.method === "POST_FORM" ||
                    action.method === "LEGACY_FUNCTION"
                ) {
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
    window.obtenerFechaConsolidadoWorkflow = obtenerFechaConsolidadoWorkflow;
    window.asegurarAliasesResultadoConsolidadoWorkflow = asegurarAliasesResultadoConsolidadoWorkflow;
    window.inicializarConsolidadoWorkflow = inicializarConsolidadoWorkflow;
    window.seleccionarConexionConsolidadoWorkflow = seleccionarConexionConsolidadoWorkflow;
    window.getLegacyWorkflowFunction = getLegacyWorkflowFunction;
    window.actualizarEstadoConsolidadoGestionDirecto = actualizarEstadoConsolidadoGestionDirecto;
    window.estadoConsolidadoGestionWorkflow = estadoConsolidadoGestionWorkflow;
    window.actualizarEstadoFaseCDirecto = actualizarEstadoFaseCDirecto;
    window.calcularEstadoOcrWorkflow = calcularEstadoOcrWorkflow;
    window.actualizarNombreArchivosOcrWorkflow = actualizarNombreArchivosOcrWorkflow;
    window.mostrarModoManualWorkflow = mostrarModoManualWorkflow;
    window.mostrarModoOcrWorkflow = mostrarModoOcrWorkflow;
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
