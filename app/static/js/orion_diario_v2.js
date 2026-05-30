
(function () {
    "use strict";

    const DEFAULT_RUTAS = [
        "\\\\10.24.90.118\\Vencorp\\COBRANZA %\\2024\\Prueba _carga_diaria_Aster_voip\\Orion",
        "Z:\\COBRANZA %\\2024\\Prueba _carga_diaria_Aster_voip\\Orion",
        "D:\\Develop\\ETL\\Nicaragua_Proceso\\unidad_red_orion\\COBRANZA %\\2024\\Prueba _carga_diaria_Aster_voip\\Orion"
    ];

    const DEFAULT_STATE = {
        conexion: "local",
        fechaProceso: "20260429",
        mesGestion: "abril",
        rutasBase: [],
        contexto: null,
        estadisticas: null,
        phaseStatus: {},
        phaseResults: {}
    };

    const ORION_V2_ACTION_MAP = {
        "crear.carpetas": { method: "GET", endpoint: "/accion/crear-carpetas" },
        "verificar.red": { method: "GET", endpoint: "/accion/verificar-red" },
        "distribuir.preparar": { method: "GET", endpoint: "/accion/distribuir" },

        "distribuir.copiar": {
            blocked: true,
            message: "La copia requiere selección previa de archivos. Por ahora ejecútela desde la pantalla Orion actual."
        },

        "procesar.discador": { method: "GET", endpoint: "/accion/procesar-discador" },
        "procesar.causales": { method: "GET", endpoint: "/accion/procesar-causales" },
        "procesar.lotes": { method: "GET", endpoint: "/accion/procesar-lotes" },

        "ocr.procesar": {
            blocked: true,
            message: "OCR requiere carga de imágenes. Por ahora ejecútelo desde la pantalla Orion actual."
        },

        "ocr.consolidar": {
            blocked: true,
            message: "La consolidación OCR requiere totales manuales. Se conectará en el siguiente paso."
        },

        "carga.causales.verificar": { method: "POST", endpoint: "/accion/verificar-carga", tipo: "causales" },
        "carga.causales.insertar": { method: "POST", endpoint: "/accion/insertar-datos", tipo: "causales" },

        "carga.lotes.verificar": { method: "POST", endpoint: "/accion/verificar-carga", tipo: "lote" },
        "carga.lotes.insertar": { method: "POST", endpoint: "/accion/insertar-datos", tipo: "lote" },

        "carga.discador.verificar": { method: "POST", endpoint: "/accion/verificar-carga", tipo: "discador" },
        "carga.discador.insertar": { method: "POST", endpoint: "/accion/insertar-datos", tipo: "discador" },

        "consolidado.gestion.consultar": { method: "POST", endpoint: "/accion/consolidar-consulta" }
    };

    const $ = (selector) => document.querySelector(selector);

    let state = loadState();

    function loadState() {
        try {
            const raw = JSON.parse(localStorage.getItem("orion_diario_v2_state") || "{}");
            return {
                ...DEFAULT_STATE,
                ...raw,
                phaseStatus: raw.phaseStatus || {},
                phaseResults: raw.phaseResults || {}
            };
        } catch {
            return { ...DEFAULT_STATE };
        }
    }

    function saveState() {
        localStorage.setItem("orion_diario_v2_state", JSON.stringify(state));
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function fmt(value) {
        if (value === null || value === undefined || value === "") return "--";
        if (typeof value === "number") return value.toLocaleString("es-BO");

        const n = Number(value);
        if (!Number.isNaN(n) && String(value).trim() !== "") {
            return n.toLocaleString("es-BO");
        }

        return value;
    }

    function ensureDebugPanel() {
        let panel = document.getElementById("odv2-debug-panel");

        if (!panel) {
            panel = document.createElement("div");
            panel.id = "odv2-debug-panel";
            panel.className = "odv2-debug-panel";
            panel.innerHTML = "Listo.";
            document.body.appendChild(panel);
        }

        return panel;
    }

    function debug(message, type = "info") {
        const panel = ensureDebugPanel();
        panel.className = "odv2-debug-panel " + type;
        panel.innerHTML = escapeHtml(message);
        console.log("[Orion Diario V2]", message);
    }

    function restoreInputs() {
        const fecha = $("#odv2-fecha-proceso");
        const mes = $("#odv2-mes-gestion");

        if (fecha) fecha.value = state.fechaProceso;
        if (mes) mes.value = state.mesGestion;

        setActiveConnection();
    }

    function collectInputs() {
        const fecha = $("#odv2-fecha-proceso");
        const mes = $("#odv2-mes-gestion");

        if (fecha) state.fechaProceso = fecha.value.trim() || state.fechaProceso;
        if (mes) state.mesGestion = mes.value.trim() || state.mesGestion;

        saveState();
    }

    function setActiveConnection() {
        document.querySelectorAll("[data-conn]").forEach(btn => {
            btn.classList.toggle("active", btn.dataset.conn === state.conexion);
        });
    }

    function getParams(includeRoutes) {
        collectInputs();

        const params = new URLSearchParams({
            fecha_proceso: state.fechaProceso,
            mes_gestion: state.mesGestion,
            conexion: state.conexion
        });

        if (includeRoutes) {
            const rutas = state.rutasBase && state.rutasBase.length ? state.rutasBase : DEFAULT_RUTAS;
            rutas.forEach(r => params.append("rutas_base", r));
        }

        return params;
    }

    function setGlobalStatus(text, status) {
        const el = $("#odv2-global-status");
        if (!el) return;

        el.textContent = text;
        el.className = "odv2-status-pill " + (status || "");
    }

    async function fetchJson(url) {
        const res = await fetch(url, { credentials: "same-origin" });
        const text = await res.text();

        let data;

        try {
            data = JSON.parse(text);
        } catch {
            throw new Error("Respuesta no es JSON. HTTP " + res.status + ": " + text.slice(0, 300));
        }

        if (!res.ok) {
            throw new Error(data.error || data.message || "HTTP " + res.status);
        }

        return data;
    }

    async function loadContext() {
        try {
            debug("Cargando contexto Orion...", "info");
            setGlobalStatus("Cargando contexto", "running");

            const url = "/api/orion-diario-v2/contexto?" + getParams(true).toString();
            const data = await fetchJson(url);

            state.contexto = data;
            state.estadisticas = null;

            if (!state.rutasBase.length && Array.isArray(data.rutas_red)) {
                state.rutasBase = data.rutas_red.map(r => r.base);
            }

            saveState();
            renderContext();
            clearStats();

            setGlobalStatus(data.conexion === "local" ? "Local activo" : "Remoto activo", "ok");
            debug("Contexto cargado correctamente.", "success");

        } catch (error) {
            setGlobalStatus("Error contexto", "error");
            debug("Error cargando contexto: " + (error.message || error), "error");
        }
    }

    async function loadStats() {
        try {
            debug("Ejecutando panel estadístico...", "info");
            setGlobalStatus("Calculando estadísticas", "running");

            const url = "/api/orion-diario-v2/estadisticas?" + getParams(true).toString();
            const data = await fetchJson(url);

            state.estadisticas = data;
            state.contexto = data;

            if (!state.rutasBase.length && Array.isArray(data.rutas_red)) {
                state.rutasBase = data.rutas_red.map(r => r.base);
            }

            saveState();
            renderContext();
            renderStats();

            setGlobalStatus(data.conexion === "local" ? "Local activo" : "Remoto activo", "ok");
            debug("Panel estadístico ejecutado correctamente.", "success");

        } catch (error) {
            setGlobalStatus("Error estadísticas", "error");
            debug("Error ejecutando estadísticas: " + (error.message || error), "error");
        }
    }

    function clearStats() {
        const msg = $("#odv2-metrics-message");
        const metrics = $("#odv2-metrics");
        const bars = $("#odv2-bars");
        const conn = $("#odv2-connections");

        if (msg) msg.style.display = "block";
        if (metrics) metrics.innerHTML = "";
        if (bars) bars.innerHTML = "";
        if (conn) conn.innerHTML = '<div class="odv2-empty">Ejecute el panel estadístico para ver información de conexión.</div>';
    }

    function renderContext() {
        const data = state.contexto;
        if (!data) return;

        const fecha = $("#odv2-fecha-proceso");
        const mes = $("#odv2-mes-gestion");

        if (fecha) fecha.value = data.fecha_proceso || state.fechaProceso;
        if (mes) mes.value = data.mes_gestion || state.mesGestion;

        state.fechaProceso = fecha ? fecha.value : state.fechaProceso;
        state.mesGestion = mes ? mes.value : state.mesGestion;

        renderSidebar(data);
        renderRoutes(data);
        renderLocalServers(data);
        renderPhaseBoard(data);
        saveState();
    }

    function renderStats() {
        const data = state.estadisticas;
        if (!data) return;

        const msg = $("#odv2-metrics-message");
        if (msg) msg.style.display = "none";

        renderMetrics(data);
        renderBars(data);
        renderConnections(data);
    }

    function getPhaseStatus(action) {
        return state.phaseStatus[action] || { status: "pending", label: "Pendiente" };
    }

    function setPhaseStatus(action, status, label) {
        state.phaseStatus[action] = { status, label };
        saveState();

        const el = document.getElementById(phaseStatusId(action));
        if (el) {
            el.className = "odv2-phase-status " + status;
            el.textContent = label;
        }

        renderSidebar(state.contexto || {});
    }

    function setPhaseResult(action, html) {
        state.phaseResults[action] = html;
        saveState();

        const el = document.getElementById(phaseResultId(action));
        if (el) el.innerHTML = html;
    }

    function phaseResultId(actionName) {
        return "odv2-result-" + String(actionName || "").replace(/[^a-zA-Z0-9_-]/g, "-");
    }

    function phaseStatusId(actionName) {
        return "odv2-status-" + String(actionName || "").replace(/[^a-zA-Z0-9_-]/g, "-");
    }

    function looksLikeError(html) {
        const text = String(html || "").toLowerCase();

        return (
            text.includes("❌") ||
            text.includes("error") ||
            text.includes("traceback") ||
            text.includes("falló") ||
            text.includes("fallo") ||
            text.includes("no se encontró") ||
            text.includes("exception")
        );
    }

    function buildWorkflowForm(meta) {
        collectInputs();

        const form = new FormData();
        form.append("fecha", state.fechaProceso);
        form.append("fecha_proceso", state.fechaProceso);
        form.append("mes_gestion", state.mesGestion);
        form.append("conexion", state.conexion);

        if (meta.tipo) {
            form.append("tipo", meta.tipo);
        }

        return form;
    }

    async function executeWorkflowAction(actionName, button) {
        const meta = ORION_V2_ACTION_MAP[actionName];

        if (!meta) {
            setPhaseResult(actionName, `<div class="odv2-result-warning">Acción no mapeada: ${escapeHtml(actionName)}</div>`);
            setPhaseStatus(actionName, "warning", "Sin mapa");
            return;
        }

        if (meta.blocked) {
            setPhaseResult(actionName, `<div class="odv2-result-warning">${escapeHtml(meta.message)}</div>`);
            setPhaseStatus(actionName, "warning", "Pendiente");
            return;
        }

        try {
            collectInputs();

            button.disabled = true;
            button.classList.add("loading");

            setPhaseStatus(actionName, "running", "Ejecutando");
            setPhaseResult(actionName, `<div class="odv2-result-loading">Ejecutando ${escapeHtml(actionName)}...</div>`);

            let response;

            if (meta.method === "GET") {
                const params = new URLSearchParams({
                    fecha: state.fechaProceso,
                    fecha_proceso: state.fechaProceso,
                    mes_gestion: state.mesGestion,
                    conexion: state.conexion,
                    _: Date.now().toString()
                });

                response = await fetch(meta.endpoint + "?" + params.toString(), {
                    method: "GET",
                    credentials: "same-origin"
                });
            } else {
                response = await fetch(meta.endpoint + "?_=" + Date.now(), {
                    method: "POST",
                    body: buildWorkflowForm(meta),
                    credentials: "same-origin"
                });
            }

            const html = await response.text();
            const error = !response.ok || looksLikeError(html);

            const wrapped = `
                <div class="odv2-result-toolbar">
                    <strong>${escapeHtml(actionName)}</strong>
                    <span>HTTP ${response.status}</span>
                </div>
                <div class="odv2-result-html">${html}</div>
            `;

            setPhaseResult(actionName, wrapped);
            setPhaseStatus(actionName, error ? "error" : "success", error ? "Error" : "Correcto");

            debug(
                error ? "La fase devolvió advertencia/error: " + actionName : "Fase ejecutada correctamente: " + actionName,
                error ? "error" : "success"
            );

            // IMPORTANTE:
            // No llamar loadStats() aquí, porque reconstruye el tablero y borra resultados.
            // El panel estadístico se ejecuta solo con su botón, como pidió el usuario.

        } catch (error) {
            setPhaseResult(actionName, `<div class="odv2-result-error">Error ejecutando ${escapeHtml(actionName)}: ${escapeHtml(error.message || error)}</div>`);
            setPhaseStatus(actionName, "error", "Error");
            debug("Error ejecutando fase " + actionName + ": " + (error.message || error), "error");
        } finally {
            button.disabled = false;
            button.classList.remove("loading");
        }
    }

    function renderSidebar(data) {
        const root = $("#odv2-sidebar-phases");
        if (!root) return;

        if (!data.fases || !data.fases.length) {
            root.innerHTML = '<div class="odv2-empty">Cargue contexto para ver fases.</div>';
            return;
        }

        root.innerHTML = "";

        data.fases.forEach(f => {
            const action = f.accion || "";
            const st = getPhaseStatus(action);

            const div = document.createElement("div");
            div.className = "odv2-phase-mini";
            div.innerHTML = `
                <span><b>${escapeHtml(f.codigo)}</b>${escapeHtml(f.nombre)}</span>
                <span class="odv2-badge ${escapeHtml(st.status)}">${escapeHtml(st.label)}</span>
            `;

            root.appendChild(div);
        });
    }

    function renderRoutes(data) {
        const root = $("#odv2-routes");
        if (!root) return;

        root.innerHTML = "";

        if (Array.isArray(data.rutas_red)) {
            data.rutas_red.forEach(r => {
                const div = document.createElement("div");
                div.className = "odv2-route";
                div.innerHTML = `
                    <small>${escapeHtml(r.nombre)}</small>
                    <strong>Base:</strong> ${escapeHtml(r.base)}<br>
                    <strong>Mes gestión:</strong> ${escapeHtml(r.ruta_mes)}
                `;
                root.appendChild(div);
            });
        }

        if (data.rutas_locales) {
            Object.entries(data.rutas_locales).forEach(([k, v]) => {
                const div = document.createElement("div");
                div.className = "odv2-route";
                div.innerHTML = `<small>${escapeHtml(k)}</small>${escapeHtml(v)}`;
                root.appendChild(div);
            });
        }

        renderPathsForm();
    }

    function renderLocalServers(data) {
        const root = $("#odv2-local-servers");
        if (!root) return;

        if (!data.servidores_locales || !data.servidores_locales.length) {
            root.innerHTML = '<div class="odv2-empty">Esta información solo se muestra para conexión LOCAL.</div>';
            return;
        }

        root.innerHTML = `
            <table class="odv2-table">
                <thead>
                    <tr>
                        <th>Tipo</th>
                        <th>Servidor</th>
                        <th>BD</th>
                        <th>Uso</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.servidores_locales.map(s => `
                        <tr>
                            <td>${escapeHtml(s.tipo)}</td>
                            <td>${escapeHtml(s.servidor)}</td>
                            <td>${escapeHtml(s.base_datos || "--")}</td>
                            <td>${escapeHtml(s.uso || "--")}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    function renderPhaseBoard(data) {
        const root = $("#odv2-phase-board");
        if (!root) return;

        if (!data.fases || !data.fases.length) {
            root.innerHTML = '<div class="odv2-empty">Cargue contexto para ver fases.</div>';
            return;
        }

        root.innerHTML = "";

        data.fases.forEach(f => {
            const action = f.accion || "";
            const st = getPhaseStatus(action);
            const resultHtml = state.phaseResults[action] || '<div class="odv2-empty">Resultado pendiente.</div>';

            const item = document.createElement("div");
            item.className = "odv2-phase";

            item.innerHTML = `
                <div class="odv2-phase-head">
                    <span>${escapeHtml(f.codigo)} — ${escapeHtml(f.nombre)}</span>
                    <span id="${phaseStatusId(action)}" class="odv2-phase-status ${escapeHtml(st.status)}">${escapeHtml(st.label)}</span>
                </div>
                <div class="odv2-phase-body">
                    <div>
                        <strong>${escapeHtml(f.grupo)}</strong><br>
                        ${escapeHtml(f.descripcion)}
                        <div class="odv2-phase-action-code">${escapeHtml(action)}</div>
                    </div>
                    <button class="odv2-run" data-phase="${escapeHtml(f.codigo)}" data-action="${escapeHtml(action)}">Ejecutar fase</button>
                </div>
                <div class="odv2-phase-result" id="${phaseResultId(action)}">
                    ${resultHtml}
                </div>
            `;

            root.appendChild(item);
        });

        root.querySelectorAll(".odv2-run").forEach(btn => {
            btn.addEventListener("click", () => {
                executeWorkflowAction(btn.dataset.action, btn);
            });
        });
    }

    function renderMetrics(data) {
        const root = $("#odv2-metrics");
        if (!root) return;

        root.innerHTML = "";

        data.metricas.forEach(m => {
            const card = document.createElement("div");
            card.className = "odv2-metric";
            card.innerHTML = `
                <small>${escapeHtml(m.titulo)}</small>
                <strong>${fmt(m.valor)}</strong>
                <span>${escapeHtml(m.detalle || "")}</span>
            `;
            root.appendChild(card);
        });
    }

    
    function renderBars(data) {
        const root = $("#odv2-bars");
        if (!root) return;

        root.innerHTML = "";

        const metricas = (data.metricas || [])
            .map(m => ({
                titulo: String(m.titulo || ""),
                valor: Number(m.valor || 0),
                detalle: String(m.detalle || "")
            }))
            .filter(m => !Number.isNaN(m.valor));

        const total = metricas.reduce((acc, item) => acc + Math.max(0, item.valor), 0);

        if (!metricas.length || total <= 0) {
            root.innerHTML = '<div class="odv2-empty">No hay datos suficientes para graficar.</div>';
            return;
        }

        const colors = [
            "#0ea5ff",
            "#22c55e",
            "#f59e0b",
            "#a855f7",
            "#ef4444",
            "#14b8a6"
        ];

        let start = 0;

        const segments = metricas.map((m, idx) => {
            const pct = Math.max(0, m.valor) / total * 100;
            const end = start + pct;
            const color = colors[idx % colors.length];
            const segment = `${color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
            start = end;
            return segment;
        });

        const pie = document.createElement("div");
        pie.className = "odv2-pie-wrap";
        pie.innerHTML = `
            <div class="odv2-pie" style="background: conic-gradient(${segments.join(", ")});">
                <div class="odv2-pie-center">
                    <strong>${fmt(total)}</strong>
                    <span>Total</span>
                </div>
            </div>
            <div class="odv2-pie-legend">
                ${metricas.map((m, idx) => {
                    const pct = total > 0 ? (Math.max(0, m.valor) / total * 100) : 0;
                    const color = colors[idx % colors.length];

                    return `
                        <div class="odv2-pie-legend-row">
                            <i style="background:${color}"></i>
                            <span>${escapeHtml(m.titulo)}</span>
                            <b>${fmt(m.valor)}</b>
                            <em>${pct.toFixed(1)}%</em>
                        </div>
                    `;
                }).join("")}
            </div>
        `;

        root.appendChild(pie);
    }


    function renderConnections(data) {
        const root = $("#odv2-connections");
        if (!root) return;

        if (!data.conexiones || !data.conexiones.length) {
            root.innerHTML = '<div class="odv2-empty">No hay conexiones para mostrar.</div>';
            return;
        }

        root.innerHTML = `
            <table class="odv2-table">
                <thead>
                    <tr>
                        <th>Proceso</th>
                        <th>Origen</th>
                        <th>Destino</th>
                        <th>Servidor</th>
                        <th>BD</th>
                        <th>Tabla</th>
                        <th>Ruta</th>
                        <th>Total</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.conexiones.map(c => `
                        <tr>
                            <td>${escapeHtml(c.proceso)}</td>
                            <td>${escapeHtml(c.origen)}</td>
                            <td>${escapeHtml(c.destino)}</td>
                            <td>${escapeHtml(c.servidor)}</td>
                            <td>${escapeHtml(c.base_datos)}</td>
                            <td>${escapeHtml(c.tabla)}</td>
                            <td>${escapeHtml(c.ruta)}</td>
                            <td>${fmt(c.total)}</td>
                            <td>${escapeHtml(c.estado)}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    function renderPathsForm() {
        const root = $("#odv2-paths-form");
        if (!root) return;

        root.innerHTML = "";

        const rutas = state.rutasBase && state.rutasBase.length ? state.rutasBase : DEFAULT_RUTAS;

        rutas.forEach((ruta, idx) => {
            const div = document.createElement("div");
            div.className = "odv2-field";
            div.innerHTML = `
                <label>Ruta base ${idx + 1}</label>
                <input data-path-index="${idx}" value="${escapeHtml(ruta)}">
            `;
            root.appendChild(div);
        });
    }

    function setupModal() {
        const edit = $("#odv2-edit-paths");
        const close = $("#odv2-close-modal");
        const save = $("#odv2-save-paths");
        const reset = $("#odv2-reset-paths");
        const modal = $("#odv2-paths-modal");

        if (edit && modal) {
            edit.addEventListener("click", () => {
                renderPathsForm();
                modal.classList.add("show");
            });
        }

        if (close && modal) {
            close.addEventListener("click", () => {
                modal.classList.remove("show");
            });
        }

        if (save && modal) {
            save.addEventListener("click", () => {
                state.rutasBase = Array.from(document.querySelectorAll("[data-path-index]"))
                    .map(input => input.value.trim())
                    .filter(Boolean);

                saveState();
                modal.classList.remove("show");
                loadContext();
            });
        }

        if (reset) {
            reset.addEventListener("click", () => {
                state.rutasBase = [];
                saveState();
                renderPathsForm();
            });
        }
    }

    function setupCollapsibles() {
        document.querySelectorAll(".odv2-collapsible").forEach(card => {
            const key = "orion_v2_collapse_" + card.dataset.collapseKey;
            const collapsed = localStorage.getItem(key) === "1";

            card.classList.toggle("odv2-collapsed", collapsed);

            const head = card.querySelector(".odv2-card-head");
            if (!head) return;

            head.addEventListener("click", () => {
                const isCollapsed = card.classList.toggle("odv2-collapsed");
                localStorage.setItem(key, isCollapsed ? "1" : "0");
            });
        });
    }

    function setupEvents() {
        document.querySelectorAll("[data-conn]").forEach(btn => {
            btn.addEventListener("click", () => {
                state.conexion = btn.dataset.conn;
                saveState();
                setActiveConnection();
                debug("Conexión seleccionada: " + state.conexion, "info");
            });
        });

        const btnContext = $("#odv2-load-context");
        if (btnContext) {
            btnContext.addEventListener("click", loadContext);
        }

        const btnStats = $("#odv2-load-stats");
        if (btnStats) {
            btnStats.addEventListener("click", loadStats);
        }
    }

    function init() {
        restoreInputs();
        setupEvents();
        setupModal();
        setupCollapsibles();
        ensureDebugPanel();

        if (state.contexto) {
            renderContext();
        }

        if (state.estadisticas) {
            renderStats();
        }

        debug("Orion Diario V2 JS cargado. Presione Cargar contexto.", "info");
    }

    document.addEventListener("DOMContentLoaded", init);
})();
