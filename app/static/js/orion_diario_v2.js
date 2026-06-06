
(function () {
    "use strict";

    const DEFAULT_RUTAS = [];

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
            message: "Primero ejecute D - Distribuir Archivos. Luego use Copiar seleccionados dentro del resultado."
        },

        "procesar.discador": { method: "GET", endpoint: "/accion/procesar-discador" },
        "procesar.causales": { method: "GET", endpoint: "/accion/procesar-causales" },
        "procesar.lotes": { method: "GET", endpoint: "/accion/procesar-lotes" },
        "comparar.lotes": { method: "GET", endpoint: "/accion/comparar-lotes" },

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
            const rawText = localStorage.getItem("orion_diario_v2_state") || "{}";

            // Si el estado quedó enorme por guardar resultados HTML,
            // se limpia para evitar pantalla negra o navegador lento.
            if (rawText.length > 250000) {
                localStorage.removeItem("orion_diario_v2_state");
                return { ...DEFAULT_STATE };
            }

            const raw = JSON.parse(rawText);

            const phaseResults = raw.phaseResults || {};

            // Nunca restaurar HTML pesado de Distribuir.
            if (phaseResults["distribuir.preparar"]) {
                phaseResults["distribuir.preparar"] = '<div class="odv2-empty">Resultado de distribución limpiado para evitar lentitud. Ejecute nuevamente D - Distribuir Archivos.</div>';
            }

            return {
                ...DEFAULT_STATE,
                ...raw,
                phaseStatus: raw.phaseStatus || {},
                phaseResults
            };
        } catch {
            localStorage.removeItem("orion_diario_v2_state");
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

    function getActiveRoutes() {
        return state.rutasBase || [];
    }

    function getParams(includeRoutes) {
        collectInputs();

        // Las rutas ya no son fuente de verdad en JavaScript.
        // Python lee LOCAL/REMOTO desde instance/orion_aster_config.json.
        return new URLSearchParams({
            fecha_proceso: state.fechaProceso,
            mes_gestion: state.mesGestion,
            conexion: state.conexion
        });
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

    function resetVisualStateForNewContext() {
        state.contexto = null;
        state.estadisticas = null;
        state.phaseStatus = {};
        state.phaseResults = {};

        const ids = [
            "odv2-sidebar-phases",
            "odv2-routes",
            "odv2-local-servers",
            "odv2-phase-board",
            "odv2-metrics",
            "odv2-bars",
            "odv2-connections"
        ];

        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.innerHTML = '<div class="odv2-empty">Cargando nuevo contexto...</div>';
            }
        });

        const msg = document.getElementById("odv2-metrics-message");
        if (msg) {
            msg.style.display = "block";
            msg.textContent = "El panel estadístico no se carga automáticamente. Presione “Ejecutar panel estadístico”.";
        }
    }

    async function loadContext() {
        try {
            collectInputs();

            resetVisualStateForNewContext();
            saveState();

            debug("Reiniciando pantalla y cargando contexto Orion...", "info");
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
            debug("Contexto cargado correctamente. La pantalla inició de nuevo.", "success");

        } catch (error) {
            setGlobalStatus("Error contexto", "error");
            debug("Error cargando contexto: " + (error.message || error), "error");
        }
    }

    async function loadStats() {
        try {
            collectInputs();

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

        if (msg) {
            msg.style.display = "block";
            msg.textContent = "El panel estadístico no se carga automáticamente. Presione “Ejecutar panel estadístico”.";
        }

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
        renderPie(data);
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
        // El resultado de Distribuir puede contener tablas/listas grandes.
        // Se muestra en pantalla, pero NO se guarda completo en localStorage.
        if (action === "distribuir.preparar") {
            state.phaseResults[action] = '<div class="odv2-empty">Distribución ejecutada. Resultado no persistido para evitar lentitud.</div>';
        } else {
            state.phaseResults[action] = html;
        }

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


/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_BEGIN === */

    function odv2DistEmptyCounts() {
        return { Causales: 0, Lotes: 0, Discador: 0 };
    }

    function odv2DistCountKey(categoria) {
        const value = String(categoria || "").trim();

        if (value.toLowerCase().includes("causal")) return "Causales";
        if (value.toLowerCase().includes("lote")) return "Lotes";
        if (value.toLowerCase().includes("discador")) return "Discador";

        return value || "Otros";
    }

    function odv2DistCollect() {
        const checks = Array.from(document.querySelectorAll("#odv2-distribucion-mvc input[type='checkbox'][data-categoria][data-archivo]"));

        const encontrados = odv2DistEmptyCounts();
        const seleccionados = odv2DistEmptyCounts();
        const payload = [];

        checks.forEach(cb => {
            const categoria = cb.dataset.categoria;
            const archivo = cb.dataset.archivo;
            const key = odv2DistCountKey(categoria);

            if (!(key in encontrados)) encontrados[key] = 0;
            if (!(key in seleccionados)) seleccionados[key] = 0;

            encontrados[key] += 1;

            if (cb.checked) {
                seleccionados[key] += 1;
                payload.push({ categoria, archivo });
            }
        });

        return { encontrados, seleccionados, payload };
    }

    function odv2DistTotal(counts) {
        return Object.values(counts || {}).reduce((a, b) => a + Number(b || 0), 0);
    }

    function odv2DistPie(counts, title) {
        const rows = [
            { key: "Causales", label: "Cau", color: "#0ea5ff" },
            { key: "Lotes", label: "Lot", color: "#f59e0b" },
            { key: "Discador", label: "Dis", color: "#22c55e" },
        ];

        const total = odv2DistTotal(counts);

        if (!total) {
            return `
                <div class="odv2-dist-pie-card">
                    <strong>${escapeHtml(title)}</strong>
                    <div class="odv2-dist-pie-empty">0</div>
                </div>
            `;
        }

        let start = 0;

        const segments = rows.map(row => {
            const value = Number(counts[row.key] || 0);
            const pct = value / total * 100;
            const end = start + pct;
            const segment = `${row.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
            start = end;
            return segment;
        });

        return `
            <div class="odv2-dist-pie-card">
                <strong>${escapeHtml(title)}</strong>
                <div class="odv2-dist-pie-stage">
                    <div class="odv2-dist-pie" style="background: conic-gradient(${segments.join(", ")});">
                        <div class="odv2-dist-pie-center">
                            <b>${fmt(total)}</b>
                            <span>${escapeHtml(title)}</span>
                        </div>
                    </div>

                    ${rows.map((row, idx) => `
                        <div class="odv2-dist-pie-value odv2-dist-pie-value-${idx}">
                            <i style="background:${row.color}"></i>
                            <span>${row.label}</span>
                            <b>${fmt(counts[row.key] || 0)}</b>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    function odv2DistSummaryTable(encontrados, seleccionados, copiados) {
        const rows = ["Causales", "Lotes", "Discador"];
        const totalEncontrados = odv2DistTotal(encontrados);
        const totalSeleccionados = odv2DistTotal(seleccionados);
        const totalCopiados = odv2DistTotal(copiados);

        return `
            <table class="odv2-table odv2-dist-summary-table">
                <thead>
                    <tr>
                        <th>Tipo</th>
                        <th>Total encontrados</th>
                        <th>Total seleccionados</th>
                        <th>Total copiados</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(row => `
                        <tr>
                            <td>${row}</td>
                            <td>${fmt(encontrados[row] || 0)}</td>
                            <td>${fmt(seleccionados[row] || 0)}</td>
                            <td>${fmt(copiados[row] || 0)}</td>
                        </tr>
                    `).join("")}
                    <tr class="odv2-dist-total-row">
                        <td>Total</td>
                        <td>${fmt(totalEncontrados)}</td>
                        <td>${fmt(totalSeleccionados)}</td>
                        <td>${fmt(totalCopiados)}</td>
                    </tr>
                </tbody>
            </table>
        `;
    }

    function odv2DistRenderSummary(copiados = null) {
        const root = document.getElementById("odv2-distribucion-mvc");
        if (!root) return;

        const data = odv2DistCollect();
        const copiedCounts = copiados || odv2DistEmptyCounts();

        const target = document.getElementById("odv2-dist-summary");

        if (!target) return;

        target.innerHTML = `
            <div class="odv2-dist-summary-layout">
                <div class="odv2-dist-summary-table-side">
                    <div class="odv2-dist-pies-title">Resumen de archivos</div>
                    ${odv2DistSummaryTable(data.encontrados, data.seleccionados, copiedCounts)}
                </div>

                <div class="odv2-dist-summary-pies-side">
                    <div class="odv2-dist-pies-title">Resumen visual</div>
                    <div class="odv2-dist-pies odv2-dist-pies-stacked">
                        ${odv2DistPie(data.encontrados, "Antes")}
                        ${odv2DistPie(copiedCounts, "Después")}
                    </div>
                </div>
            </div>
        `;
    }

    function odv2DistCopiedCounts(detalle) {
        const counts = odv2DistEmptyCounts();

        (detalle || []).forEach(item => {
            const key = odv2DistCountKey(item.categoria);
            if (!(key in counts)) counts[key] = 0;
            counts[key] += 1;
        });

        return counts;
    }

    function odv2DistRender(data) {
        const grupos = data.grupos || [];

        const html = `
            <div id="odv2-distribucion-mvc" class="odv2-dist-box">
                <div class="odv2-dist-head">
                    <div>
                        <h4>Distribución de archivos Orion</h4>
                        <p>Seleccione los archivos a copiar. Todos vienen marcados por defecto.</p>
                        <small>Ruta usada: ${escapeHtml(data.red_base_usada || "--")}</small>
                    </div>
                </div>

                <div class="odv2-dist-selection">
                    ${grupos.map(g => `
                        <details class="odv2-dist-group" open>
                            <summary>📁 ${escapeHtml(g.categoria)} - ${fmt(g.total)} archivo(s)</summary>
                            <div class="odv2-dist-routes">
                                <div><b>Ruta origen:</b> ${escapeHtml(g.ruta_origen || "--")}</div>
                                <div><b>Ruta destino:</b> ${escapeHtml(g.ruta_destino || "--")}</div>
                            </div>
                            <table class="odv2-table odv2-dist-files-table">
                                <thead>
                                    <tr>
                                        <th>Copiar</th>
                                        <th>Archivo</th>
                                        <th>Ruta origen</th>
                                        <th>Ruta destino</th>
                                        <th>Estado destino</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${(g.archivos || []).map(a => `
                                        <tr>
                                            <td>
                                                <input type="checkbox"
                                                       checked
                                                       data-categoria="${escapeHtml(a.categoria)}"
                                                       data-archivo="${escapeHtml(a.archivo)}">
                                            </td>
                                            <td><b>${escapeHtml(a.archivo)}</b></td>
                                            <td>${escapeHtml(a.ruta_origen || "")}</td>
                                            <td>${escapeHtml(a.ruta_destino || "")}</td>
                                            <td class="${a.existe_destino ? "odv2-dist-warn" : "odv2-dist-ok"}">
                                                ${a.existe_destino ? "⚠️ Ya existe, se reemplazará" : "✅ Nuevo"}
                                            </td>
                                        </tr>
                                    `).join("")}
                                </tbody>
                            </table>
                        </details>
                    `).join("")}
                </div>

                
                <div class="odv2-dist-actions">
                    <button type="button" id="odv2-dist-copy" class="odv2-dist-copy-btn">
                        Copiar seleccionados
                    </button>
                </div>

                <div id="odv2-dist-summary"></div>
                <div id="odv2-dist-result"></div>
            </div>
        `;

        setPhaseResult("distribuir.preparar", html);
        setPhaseStatus("distribuir.preparar", "success", "Correcto");

        document.querySelectorAll("#odv2-distribucion-mvc input[type='checkbox']").forEach(cb => {
            cb.addEventListener("change", () => odv2DistRenderSummary());
        });

        const btn = document.getElementById("odv2-dist-copy");
        if (btn) btn.addEventListener("click", copiarDistribucionMvc);

        odv2DistRenderSummary();
    }

    async function ejecutarDistribucionMvc(button) {
        try {
            collectInputs();

            button.disabled = true;
            button.classList.add("loading");

            setPhaseStatus("distribuir.preparar", "running", "Ejecutando");
            setPhaseResult("distribuir.preparar", `<div class="odv2-result-loading">Preparando distribución Orion v2...</div>`);

            const url = "/api/orion-diario-v2/distribucion/preparar?" + getParams(true).toString();
            const response = await fetch(url, { credentials: "same-origin" });
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Error preparando distribución.");
            }

            odv2DistRender(data);
            debug("Distribución Orion v2 preparada correctamente.", "success");

        } catch (error) {
            setPhaseStatus("distribuir.preparar", "error", "Error");
            setPhaseResult("distribuir.preparar", `<div class="odv2-result-error">Error preparando distribución: ${escapeHtml(error.message || error)}</div>`);
            debug("Error preparando distribución MVC: " + (error.message || error), "error");
        } finally {
            button.disabled = false;
            button.classList.remove("loading");
        }
    }

    async function copiarDistribucionMvc() {
        const result = document.getElementById("odv2-dist-result");
        const collected = odv2DistCollect();

        if (!collected.payload.length) {
            if (result) result.innerHTML = `<div class="odv2-result-warning">No hay archivos seleccionados para copiar.</div>`;
            return;
        }

        if (result) {
            result.innerHTML = `<div class="odv2-result-loading">Copiando ${fmt(collected.payload.length)} archivo(s)...</div>`;
        }

        try {
            const payload = {
                fecha_proceso: state.fechaProceso,
                fecha: state.fechaProceso,
                mes_gestion: state.mesGestion,
                conexion: state.conexion,
                rutas_base: getActiveRoutes(),
                seleccionados: collected.payload
            };

            const response = await fetch("/api/orion-diario-v2/distribucion/copiar?_=" + Date.now(), {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            const copiedCounts = data.success ? odv2DistCopiedCounts(data.copiados_detalle) : odv2DistEmptyCounts();
            odv2DistRenderSummary(copiedCounts);

            if (result) {
                result.innerHTML = `
                    <div class="odv2-result-toolbar">
                        <strong>Resultado copia seleccionados</strong>
                        <span>HTTP ${response.status}</span>
                    </div>
                    <div class="odv2-result-html">${data.result_html || escapeHtml(data.error || "")}</div>
                `;
            }

            setPhaseStatus("distribuir.preparar", data.success ? "success" : "error", data.success ? "Copiado" : "Error copia");
            debug(data.success ? "Copia realizada correctamente." : "Error copiando archivos.", data.success ? "success" : "error");

        } catch (error) {
            if (result) {
                result.innerHTML = `<div class="odv2-result-error">Error copiando seleccionados: ${escapeHtml(error.message || error)}</div>`;
            }

            setPhaseStatus("distribuir.preparar", "error", "Error copia");
            debug("Error copiando distribución MVC: " + (error.message || error), "error");
        }
    }

    window.OrionDistribucionMVC = {
        preparar: ejecutarDistribucionMvc,
        copiar: copiarDistribucionMvc,
    };

/* === ORION_DIARIO_V2_DISTRIBUCION_MVC_END === */



/* === ORION_DIARIO_V2_PROCESAMIENTO_MVC_BEGIN === */

    const ORION_PROC_ACTIONS = new Set([
        "procesar.discador",
        "procesar.causales",
        "procesar.lotes",
        "comparar.lotes"
    ]);

    const ORION_PROC_META = {
        "procesar.discador": {
            tipo: "Discador",
            icono: "📞",
            esperado: "Consolidado Discador",
            color: "cyan"
        },
        "procesar.causales": {
            tipo: "Causales",
            icono: "📋",
            esperado: "Causales_Consolidado.xlsx",
            color: "blue"
        },
        "procesar.lotes": {
            tipo: "Lotes",
            icono: "🧩",
            esperado: "Lotes consolidados",
            color: "green"
        }
    };

    function odv2ProcStripHtml(html) {
        const div = document.createElement("div");
        div.innerHTML = html || "";
        return div.textContent || div.innerText || "";
    }

    function odv2ProcNum(value) {
        const clean = String(value ?? "")
            .replace(/\./g, "")
            .replace(/,/g, "")
            .replace(/[^\d-]/g, "");

        if (!clean) return null;

        const n = Number(clean);
        return Number.isFinite(n) ? n : null;
    }

    function odv2ProcTableRows(html) {
        const doc = new DOMParser().parseFromString(html || "", "text/html");
        const tables = Array.from(doc.querySelectorAll("table"));
        const parsed = [];

        tables.forEach(table => {
            const headers = Array.from(table.querySelectorAll("tr:first-child th"))
                .map(th => th.textContent.trim());

            const rows = Array.from(table.querySelectorAll("tr"))
                .slice(1)
                .map(tr => Array.from(tr.querySelectorAll("td")).map(td => td.textContent.trim()))
                .filter(row => row.length);

            parsed.push({ headers, rows });
        });

        return parsed;
    }

    function odv2ProcFindMetricFromPasoTable(tables, labelIncludes) {
        const label = String(labelIncludes || "").toLowerCase();

        for (const table of tables) {
            const h = table.headers.map(x => x.toLowerCase());

            if (!(h.includes("paso") && h.includes("cantidad"))) continue;

            for (const row of table.rows) {
                const first = String(row[0] || "").toLowerCase();

                if (first.includes(label)) {
                    return odv2ProcNum(row[1]);
                }
            }
        }

        return null;
    }

    function odv2ProcFindIndicator(tables, labelIncludes) {
        const label = String(labelIncludes || "").toLowerCase();

        for (const table of tables) {
            const h = table.headers.map(x => x.toLowerCase());

            if (!(h.includes("indicador") && h.includes("valor"))) continue;

            for (const row of table.rows) {
                const first = String(row[0] || "").toLowerCase();

                if (first.includes(label)) {
                    return odv2ProcNum(row[1]);
                }
            }
        }

        return null;
    }

    function odv2ProcSumColumn(tables, headerIncludes) {
        const target = String(headerIncludes || "").toLowerCase();

        for (const table of tables) {
            const idx = table.headers.findIndex(h => String(h || "").toLowerCase().includes(target));

            if (idx < 0) continue;

            let total = 0;
            let found = false;

            for (const row of table.rows) {
                const first = String(row[0] || "").trim().toLowerCase();

                if (first === "total") {
                    const nTotal = odv2ProcNum(row[idx]);
                    if (nTotal !== null) return nTotal;
                }

                const n = odv2ProcNum(row[idx]);

                if (n !== null) {
                    total += n;
                    found = true;
                }
            }

            if (found) return total;
        }

        return null;
    }

    function odv2ProcExtract(actionName, html, httpStatus) {
        const meta = ORION_PROC_META[actionName] || {};
        const text = odv2ProcStripHtml(html);
        const textLower = text.toLowerCase();
        const tables = odv2ProcTableRows(html);

        let ok = textLower.includes("procesado correctamente") ||
         textLower.includes("procesados correctamente");

if (actionName === "comparar.lotes") {
    const tieneExitoComparacion =
        textLower.includes("todos los lotes coinciden") ||
        textLower.includes("lotes coinciden") ||
        textLower.includes("resumen excel generado");

    const tieneFalloComparacion =
        textLower.includes("no coinciden") ||
        textLower.includes("diferencias") ||
        textLower.includes("error") ||
        textLower.includes("no existe");

    ok = tieneExitoComparacion && !tieneFalloComparacion;
}

        const parsed = {
            actionName,
            tipo: meta.tipo || actionName,
            icono: meta.icono || "⚙️",
            esperado: meta.esperado || "",
            httpStatus,
            ok,
            mensaje: ok ? "Procesamiento completado correctamente." : "El procesamiento respondió con error o advertencia.",
            original: null,
            filtrado: null,
            consolidado: null,
            archivos: null,
            extra: [],
            rawHtml: html || ""
        };

        if (actionName === "procesar.discador") {
            parsed.original = odv2ProcFindMetricFromPasoTable(tables, "registros originales");
            parsed.filtrado = odv2ProcFindMetricFromPasoTable(tables, "tras filtro campaña");
            parsed.consolidado = odv2ProcFindMetricFromPasoTable(tables, "tras filtro estado");
            parsed.archivos = textLower.includes("discador usado") ? 1 : null;

            parsed.extra.push(["Fuente", "Archivo Discador"]);
            parsed.extra.push(["Salida esperada", "Reporte_Discador_*_Consolidado.xlsx"]);
        }

        if (actionName === "procesar.causales") {
            parsed.original = odv2ProcSumColumn(tables, "original");
            parsed.filtrado = odv2ProcSumColumn(tables, "tras evento");
            parsed.consolidado = odv2ProcFindIndicator(tables, "total filas consolidadas") || odv2ProcSumColumn(tables, "normalizados");
            parsed.archivos = odv2ProcFindIndicator(tables, "total archivos procesados");

            parsed.extra.push(["Fuente", "Carpeta Causales"]);
            parsed.extra.push(["Salida esperada", "Causales_Consolidado.xlsx"]);
        }

        if (actionName === "procesar.lotes") {
            parsed.original = odv2ProcSumColumn(tables, "filas orig");
            parsed.filtrado = odv2ProcSumColumn(tables, "filas tras piv");
            parsed.consolidado = parsed.filtrado;
            parsed.archivos = null;

            const lotesEncontradosMatch = text.match(/Valores únicos encontrados.*?(\d+)/i);
            if (lotesEncontradosMatch) {
                parsed.extra.push(["Valores únicos en Discador[Lote]", lotesEncontradosMatch[1]]);
            }

            parsed.extra.push(["Fuente", "Carpeta Lotes"]);
            parsed.extra.push(["Salida esperada", "Lotes consolidados"]);
        }

        return parsed;
    }

    function odv2ProcKpi(label, value, hint = "") {
        const display = value === null || value === undefined ? "--" : fmt(value);

        return `
            <div class="odv2-proc-kpi">
                <span>${escapeHtml(label)}</span>
                <strong>${display}</strong>
                ${hint ? `<em>${escapeHtml(hint)}</em>` : ""}
            </div>
        `;
    }

    function odv2ProcResumenTable(parsed) {
        const rows = [
            ["Tipo", parsed.tipo],
            ["HTTP", parsed.httpStatus],
            ["Estado", parsed.ok ? "Correcto" : "Revisar"],
            ["Archivo/Salida", parsed.esperado || "--"],
            ["Registros originales", parsed.original ?? "--"],
            ["Registros filtrados/procesados", parsed.filtrado ?? "--"],
            ["Registros consolidados", parsed.consolidado ?? "--"],
            ["Archivos procesados", parsed.archivos ?? "--"],
            ...parsed.extra
        ];

        return `
            <table class="odv2-table odv2-proc-table">
                <thead>
                    <tr>
                        <th>Indicador</th>
                        <th>Valor</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(row => `
                        <tr>
                            <td>${escapeHtml(row[0])}</td>
                            <td>${escapeHtml(row[1])}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    function odv2ProcPie(parsed) {
        const values = [
            { label: "Original", short: "Ori", color: "#0ea5ff", value: Number(parsed.original || 0) },
            { label: "Filtrado", short: "Fil", color: "#f59e0b", value: Number(parsed.filtrado || 0) },
            { label: "Consolidado", short: "Con", color: "#22c55e", value: Number(parsed.consolidado || 0) },
        ];

        const total = values.reduce((acc, item) => acc + item.value, 0);

        if (!total) {
            return `
                <div class="odv2-proc-pie-card">
                    <strong>Resumen visual</strong>
                    <div class="odv2-proc-pie-empty">--</div>
                </div>
            `;
        }

        let start = 0;

        const segments = values.map(item => {
            const pct = item.value / total * 100;
            const end = start + pct;
            const segment = `${item.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
            start = end;
            return segment;
        });

        return `
            <div class="odv2-proc-pie-card">
                <strong>Resumen visual</strong>
                <div class="odv2-proc-pie-stage">
                    <div class="odv2-proc-pie" style="background: conic-gradient(${segments.join(", ")});">
                        <div class="odv2-proc-pie-center">
                            <b>${fmt(parsed.consolidado || parsed.filtrado || 0)}</b>
                            <span>Final</span>
                        </div>
                    </div>

                    ${values.map((item, idx) => `
                        <div class="odv2-proc-pie-value odv2-proc-pie-value-${idx}">
                            <i style="background:${item.color}"></i>
                            <span>${escapeHtml(item.short)}</span>
                            <b>${fmt(item.value)}</b>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    function odv2ProcResultHtml(parsed) {
        if (parsed.actionName === "comparar.lotes") {
            return `
                <div class="odv2-proc-box odv2-comparar-lotes-simple ${parsed.ok ? "success" : "error"}">
                    <div class="odv2-proc-head">
                        <div>
                            <h4>${parsed.icono} ${escapeHtml(parsed.tipo)}</h4>
                            <p>Resultado de validación cruzada de lotes contra Discador.</p>
                        </div>
                    </div>

                    <details class="odv2-proc-details odv2-comparar-lotes-details" open>
                        <summary>Ver detalle técnico original</summary>
                        <div class="odv2-proc-original">${parsed.rawHtml}</div>
                    </details>
                </div>
            `;
        }

        return `
            <div class="odv2-proc-box ${parsed.ok ? "success" : "error"}">
                <div class="odv2-proc-head">
                    <div>
                        <h4>${parsed.icono} ${escapeHtml(parsed.tipo)}</h4>
                        <p>${escapeHtml(parsed.mensaje)}</p>
                    </div>
                    <span class="odv2-proc-chip ${parsed.ok ? "success" : "error"}">
                        ${parsed.ok ? "Correcto" : "Revisar"}
                    </span>
                </div>

                <div class="odv2-proc-kpis">
                    ${odv2ProcKpi("Original", parsed.original)}
                    ${odv2ProcKpi("Filtrado", parsed.filtrado)}
                    ${odv2ProcKpi("Consolidado", parsed.consolidado)}
                    ${odv2ProcKpi("Archivos", parsed.archivos)}
                </div>

                <div class="odv2-proc-layout">
                    <div class="odv2-proc-table-side">
                        <div class="odv2-proc-section-title">Resumen de procesamiento</div>
                        ${odv2ProcResumenTable(parsed)}
                    </div>

                    <div class="odv2-proc-visual-side">
                        ${odv2ProcPie(parsed)}
                    </div>
                </div>

                <details class="odv2-proc-details">
                    <summary>Ver detalle técnico original</summary>
                    <div class="odv2-proc-original">${parsed.rawHtml}</div>
                </details>
            </div>
        `;
    }

    async function ejecutarProcesamientoMvc(actionName, button) {
        const meta = ORION_V2_ACTION_MAP[actionName];

        if (!meta) {
            debug("Acción de procesamiento no encontrada: " + actionName, "error");
            return;
        }

        try {
            collectInputs();

            if (button) {
                button.disabled = true;
                button.classList.add("loading");
            }

            setPhaseStatus(actionName, "running", "Procesando");
            setPhaseResult(actionName, `<div class="odv2-result-loading">Procesando ${escapeHtml(ORION_PROC_META[actionName]?.tipo || actionName)}...</div>`);

            const fechaProcesoActiva = (
                document.getElementById("odv2-fecha-proceso")?.value ||
                state.fechaProceso ||
                "20260429"
            ).trim();

            // Los endpoints antiguos de procesamiento usan principalmente "fecha".
            // También enviamos "fecha_proceso" para mantener compatibilidad con Orion v2.
            const params = getParams(true);
            params.set("fecha", fechaProcesoActiva);
            params.set("fecha_proceso", fechaProcesoActiva);
            params.set("mes_gestion", state.mesGestion || "");
            params.set("conexion", state.conexion || "local");

            state.fechaProceso = fechaProcesoActiva;
            saveState();

            const url = meta.endpoint + "?" + params.toString();

            const response = await fetch(url + "&_=" + Date.now(), {
                method: "GET",
                credentials: "same-origin"
            });

            const html = await response.text();
            const parsed = odv2ProcExtract(actionName, html, response.status);

            setPhaseResult(actionName, odv2ProcResultHtml(parsed));
            const labelOk = actionName === "comparar.lotes" ? "Correcto" : "Completado";setPhaseStatus(actionName, parsed.ok ? "success" : "error", parsed.ok ? labelOk : "Revisar");

            debug(
                parsed.ok
                    ? `${parsed.tipo} procesado correctamente.`
                    : `${parsed.tipo} respondió con observaciones.`,
                parsed.ok ? "success" : "error"
            );

        } catch (error) {
            setPhaseStatus(actionName, "error", "Error");
            setPhaseResult(actionName, `<div class="odv2-result-error">Error procesando: ${escapeHtml(error.message || error)}</div>`);
            debug("Error en procesamiento MVC: " + (error.message || error), "error");

        } finally {
            if (button) {
                button.disabled = false;
                button.classList.remove("loading");
            }
        }
    }

    window.OrionProcesamientoMVC = {
        ejecutar: ejecutarProcesamientoMvc,
        extract: odv2ProcExtract
    };

/* === ORION_DIARIO_V2_PROCESAMIENTO_MVC_END === */



/* === ORION_DIARIO_V2_CARGA_SQL_PRECHECK_BEGIN === */

    const ORION_CARGA_SQL_ACTIONS = new Set([
        "carga.causales.verificar",
        "carga.causales.insertar",
        "carga.lotes.verificar",
        "carga.lotes.insertar",
        "carga.discador.verificar",
        "carga.discador.insertar"
    ]);

    const ORION_CARGA_SQL_META = {
        "carga.causales.verificar": { tipo: "causales", label: "Carga Causales", modo: "verificar", icono: "📋" },
        "carga.causales.insertar": { tipo: "causales", label: "Carga Causales", modo: "insertar", icono: "📋" },
        "carga.lotes.verificar": { tipo: "lote", label: "Carga Lotes", modo: "verificar", icono: "🧩" },
        "carga.lotes.insertar": { tipo: "lote", label: "Carga Lotes", modo: "insertar", icono: "🧩" },
        "carga.discador.verificar": { tipo: "discador", label: "Carga Discador", modo: "verificar", icono: "📞" },
        "carga.discador.insertar": { tipo: "discador", label: "Carga Discador", modo: "insertar", icono: "📞" }
    };

    function odv2CargaConexionActiva() {
        const select = document.getElementById("odv2-conexion-global");
        return (select?.value || state.conexion || "local").trim();
    }

    function odv2CargaFechaActiva() {
        return (
            document.getElementById("odv2-fecha-proceso")?.value ||
            state.fechaProceso ||
            "20260429"
        ).trim();
    }

    function odv2CargaForm(tipo) {
        collectInputs();

        const fecha = odv2CargaFechaActiva();
        const conexion = odv2CargaConexionActiva();

        state.fechaProceso = fecha;
        state.conexion = conexion;
        saveState();

        const form = new FormData();
        form.append("fecha", fecha);
        form.append("fecha_proceso", fecha);
        form.append("tipo", tipo);
        form.append("conexion", conexion);
        form.append("mes_gestion", state.mesGestion || "");

        return form;
    }

    function odv2CargaText(html) {
        const div = document.createElement("div");
        div.innerHTML = html || "";
        return div.textContent || div.innerText || "";
    }

    function odv2CargaNum(value) {
        const clean = String(value ?? "")
            .replace(/\./g, "")
            .replace(/,/g, "")
            .replace(/[^\d-]/g, "");

        if (!clean) return null;

        const n = Number(clean);
        return Number.isFinite(n) ? n : null;
    }

    function odv2CargaExtractCount(html) {
        const text = odv2CargaText(html);
        const patterns = [
            /total\s+filas\s+consolidadas\s*[:\s]+(\d+)/i,
            /registros\s+a\s+insertar\s*[:\s]+(\d+)/i,
            /registros\s+detectados\s*[:\s]+(\d+)/i,
            /total\s+registros\s*[:\s]+(\d+)/i,
            /filas\s+consolidadas\s*[:\s]+(\d+)/i,
            /insertad[oa]s?\s*[:\s]+(\d+)/i,
            /(\d+)\s+registros/i
        ];

        for (const pattern of patterns) {
            const m = text.match(pattern);
            if (m) {
                const n = odv2CargaNum(m[1]);
                if (n !== null) return n;
            }
        }

        const tableNumbers = Array.from((html || "").matchAll(/<td[^>]*>\s*([\d.,]+)\s*<\/td>/gi))
            .map(m => odv2CargaNum(m[1]))
            .filter(n => n !== null);

        if (tableNumbers.length) {
            return Math.max(...tableNumbers);
        }

        return null;
    }

    function odv2CargaDetectInserted(html) {
        const text = odv2CargaText(html).toLowerCase();

        if (text.includes("insertado") || text.includes("insertados") || text.includes("cargado")) {
            const n = odv2CargaExtractCount(html);
            return n;
        }

        return null;
    }

    function odv2CargaOkHtml(html) {
    const text = odv2CargaText(html).toLowerCase();

    const tieneFallo =
        text.includes("❌") ||
        text.includes("traceback") ||
        text.includes("exception") ||
        text.includes("error sql") ||
        text.includes("error de conexión") ||
        text.includes("error de conexion") ||
        text.includes("no existe el archivo") ||
        text.includes("archivo no encontrado") ||
        text.includes("faltan columnas") ||
        text.includes("no se pudo");

    const tieneExito =
        text.includes("puede continuar") ||
        text.includes("archivo encontrado") ||
        text.includes("verificación de") ||
        text.includes("verificacion de") ||
        text.includes("no se encontraron registros previos") ||
        text.includes("insertado") ||
        text.includes("insertados") ||
        text.includes("inserción") ||
        text.includes("insercion") ||
        text.includes("carga completada");

    return tieneExito && !tieneFallo;
}

    async function odv2CargaPrecheck(tipo) {
        const params = new URLSearchParams();
        params.set("fecha_proceso", odv2CargaFechaActiva());
        params.set("fecha", odv2CargaFechaActiva());
        params.set("tipo", tipo);
        params.set("conexion", odv2CargaConexionActiva());

        const response = await fetch("/api/orion-diario-v2/carga/precheck?" + params.toString() + "&_=" + Date.now(), {
            credentials: "same-origin"
        });

        return await response.json();
    }

    async function odv2CargaPost(endpoint, tipo) {
        const response = await fetch(endpoint + "?_=" + Date.now(), {
            method: "POST",
            credentials: "same-origin",
            body: odv2CargaForm(tipo)
        });

        const html = await response.text();

        return {
            ok: response.ok && odv2CargaOkHtml(html),
            status: response.status,
            html,
            count: odv2CargaExtractCount(html)
        };
    }

    function odv2CargaInfoTable(precheck, detectados, insertar, insertados) {
        const origen = precheck.origen || {};

        const rows = [
            ["Conexión", precheck.conexion || "--"],
            ["Servidor destino", precheck.servidor_destino || "--"],
            ["Base destino", precheck.bd_destino || "--"],
            ["Tabla destino", precheck.tabla_destino || "--"],
            ["Columna fecha control", precheck.fecha_columna || "--"],
            ["Fecha proceso", precheck.fecha_sql || precheck.fecha_proceso || "--"],
            ["Ruta/archivo origen", origen.archivo_principal || origen.base_orion || "--"],
            ["Archivos origen detectados", origen.total_archivos ?? "--"],
            ["Registros existentes con fecha", precheck.registros_existentes ?? "--"],
            ["Registros detectados", detectados ?? "--"],
            ["Registros a insertar", insertar ?? "--"],
            ["Registros insertados", insertados ?? "--"]
        ];

        return `
            <table class="odv2-table odv2-carga-sql-table">
                <thead>
                    <tr>
                        <th>Elemento</th>
                        <th>Detalle</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(row => `
                        <tr>
                            <td>${escapeHtml(row[0])}</td>
                            <td>${escapeHtml(row[1])}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    function odv2CargaMetric(label, value, tone = "") {
        return `
            <div class="odv2-carga-sql-metric ${tone}">
                <span>${escapeHtml(label)}</span>
                <strong>${value === null || value === undefined ? "--" : fmt(value)}</strong>
            </div>
        `;
    }

    function odv2CargaRender({
        meta,
        precheck,
        verificar = null,
        insertar = null,
        blocked = false,
        mode = "verificar"
    }) {
        const duplicado = Number(precheck.registros_existentes || 0) > 0;
        const detectados = verificar?.count ?? null;
        const aInsertar = duplicado ? 0 : detectados;
        const insertados = insertar ? odv2CargaDetectInserted(insertar.html) : null;

        const precheckValido = Boolean(precheck.ok) && Boolean(precheck.fecha_columna);
        const bloqueadoPorPrecheck = Boolean(blocked) || Boolean(duplicado) || !precheckValido;
        const statusClass = bloqueadoPorPrecheck ? "blocked" : "ok";

        return `
            <div class="odv2-carga-sql-box ${statusClass}">
                <div class="odv2-carga-sql-head">
                    <div>
                        <h4>${meta.icono} ${escapeHtml(meta.label)}</h4>
                        <p>${escapeHtml(precheck.mensaje || "")}</p>
                    </div>
                    <span class="odv2-carga-sql-chip ${statusClass}">
                        ${duplicado ? "Duplicado detectado" : (insertar ? "Inserción ejecutada" : "Verificación")}
                    </span>
                </div>

                <div class="odv2-carga-sql-metrics">
                    ${odv2CargaMetric("Existentes", precheck.registros_existentes, duplicado ? "danger" : "ok")}
                    ${odv2CargaMetric("Detectados", detectados)}
                    ${odv2CargaMetric("A insertar", aInsertar, duplicado ? "danger" : "ok")}
                    ${odv2CargaMetric("Insertados", insertados)}
                </div>

                ${!precheckValido ? `
                    <div class="odv2-carga-sql-alert danger">
                        ❌ No se pudo validar correctamente la columna de fecha de control. La inserción queda bloqueada hasta corregir la tabla o definir la columna de fecha.
                    </div>
                ` : duplicado ? `
                    <div class="odv2-carga-sql-alert danger">
                        ❌ Ya existen registros para la fecha del proceso. La inserción fue bloqueada para evitar duplicar información.
                    </div>
                ` : `
                    <div class="odv2-carga-sql-alert ok">
                        ✅ No se encontraron registros previos para la fecha del proceso. Puede continuar con la carga.
                    </div>
                `}

                <div class="odv2-carga-sql-layout">
                    <div>
                        <div class="odv2-carga-sql-title">Información origen / destino</div>
                        ${odv2CargaInfoTable(precheck, detectados, aInsertar, insertados)}
                    </div>
                </div>

                <details class="odv2-carga-sql-details" ${mode === "verificar" ? "open" : ""}>
                    <summary>Resultado de verificación</summary>
                    <div class="odv2-carga-sql-original">
                        ${verificar?.html || "<div class='odv2-empty'>Sin verificación ejecutada.</div>"}
                    </div>
                </details>

                <details class="odv2-carga-sql-details" ${insertar ? "open" : ""}>
                    <summary>Resultado de inserción</summary>
                    <div class="odv2-carga-sql-original">
                        ${insertar?.html || (duplicado ? "<div class='odv2-result-warning'>Inserción bloqueada por registros existentes.</div>" : "<div class='odv2-empty'>Inserción no ejecutada.</div>")}
                    </div>
                </details>
            </div>
        `;
    }

    async function ejecutarCargaSqlMvc(actionName, button) {
        const meta = ORION_CARGA_SQL_META[actionName];
        const action = ORION_V2_ACTION_MAP[actionName];

        if (!meta || !action) {
            debug("Acción de carga no registrada: " + actionName, "error");
            return;
        }

        try {
            collectInputs();

            if (button) {
                button.disabled = true;
                button.classList.add("loading");
            }

            setPhaseStatus(actionName, "running", "Validando");
            setPhaseResult(actionName, `<div class="odv2-result-loading">Validando duplicados y preparando ${escapeHtml(meta.label)}...</div>`);

            const precheck = await odv2CargaPrecheck(meta.tipo);

            if (!precheck.ok) {
                setPhaseStatus(actionName, "error", "Error precheck");
                setPhaseResult(actionName, odv2CargaRender({
                    meta,
                    precheck,
                    blocked: true,
                    mode: meta.modo
                }));
                debug("No se pudo validar duplicados para " + meta.label, "error");
                return;
            }

            if (Number(precheck.registros_existentes || 0) > 0) {
                setPhaseStatus(actionName, "blocked", "Duplicado");
                setPhaseResult(actionName, odv2CargaRender({
                    meta,
                    precheck,
                    blocked: true,
                    mode: meta.modo
                }));
                debug("Inserción bloqueada: existen registros para la fecha.", "error");
                return;
            }

            const verificacion = await odv2CargaPost("/accion/verificar-carga", meta.tipo);

            if (meta.modo === "verificar") {
                setPhaseStatus(actionName, verificacion.ok ? "success" : "error", verificacion.ok ? "Verificado" : "Revisar");
                setPhaseResult(actionName, odv2CargaRender({
                    meta,
                    precheck,
                    verificar: verificacion,
                    mode: "verificar"
                }));
                debug(meta.label + " verificado.", verificacion.ok ? "success" : "error");
                return;
            }

            const insercion = await odv2CargaPost("/accion/insertar-datos", meta.tipo);

            setPhaseStatus(actionName, insercion.ok ? "success" : "error", insercion.ok ? "Insertado" : "Revisar");
            setPhaseResult(actionName, odv2CargaRender({
                meta,
                precheck,
                verificar: verificacion,
                insertar: insercion,
                mode: "insertar"
            }));

            debug(meta.label + " inserción finalizada.", insercion.ok ? "success" : "error");

        } catch (error) {
            setPhaseStatus(actionName, "error", "Error");
            setPhaseResult(actionName, `<div class="odv2-result-error">Error en carga SQL: ${escapeHtml(error.message || error)}</div>`);
            debug("Error en carga SQL MVC: " + (error.message || error), "error");

        } finally {
            if (button) {
                button.disabled = false;
                button.classList.remove("loading");
            }
        }
    }

    window.OrionCargaSqlMVC = {
        ejecutar: ejecutarCargaSqlMvc,
        precheck: odv2CargaPrecheck
    };

/* === ORION_DIARIO_V2_CARGA_SQL_PRECHECK_END === */



/* === ORION_DIARIO_V2_CARGA_SQL_INLINE_CLEAN_BEGIN === */

    const ORION_CARGA_INLINE_DEFS = [
        {
            verificar: "carga.causales.verificar",
            insertar: "carga.causales.insertar",
            label: "Insertar Datos Causales"
        },
        {
            verificar: "carga.lotes.verificar",
            insertar: "carga.lotes.insertar",
            label: "Insertar Datos Lotes"
        },
        {
            verificar: "carga.discador.verificar",
            insertar: "carga.discador.insertar",
            label: "Insertar Datos Discador"
        }
    ];

    function odv2CargaInlineFindCard(actionName) {
        let node = document.querySelector(`[data-action="${actionName}"]`);

        if (!node) {
            const btn = document.querySelector(`button[data-action="${actionName}"], .odv2-run[data-action="${actionName}"]`);
            node = btn ? btn.closest(".odv2-phase-card, .odv2-card, .odv2-phase, section, article, details, div") : null;
        }

        if (!node) return null;

        if (node.tagName === "BUTTON" || node.tagName === "A") {
            node = node.closest(".odv2-phase-card, .odv2-card, .odv2-phase, section, article, details, div");
        }

        return node;
    }

    function odv2CargaInlineRemoveWrongInsertCards() {
        ORION_CARGA_INLINE_DEFS.forEach(def => {
            document.querySelectorAll(`[data-action="${def.insertar}"]`).forEach(node => {
                if (node.classList && node.classList.contains("odv2-carga-inline-insert-btn")) return;

                const tag = String(node.tagName || "").toLowerCase();

                if (tag === "button" || tag === "a") return;

                const looksLikePhase =
                    node.classList.contains("odv2-phase-card") ||
                    node.classList.contains("odv2-card") ||
                    node.querySelector?.(".odv2-phase-title, h4, .odv2-run, button");

                if (looksLikePhase) {
                    node.remove();
                }
            });
        });
    }

    function odv2CargaInlineEnsureButtons() {
        if (typeof ejecutarCargaSqlMvc !== "function") {
            return;
        }

        odv2CargaInlineRemoveWrongInsertCards();

        ORION_CARGA_INLINE_DEFS.forEach(def => {
            const card = odv2CargaInlineFindCard(def.verificar);

            if (!card) return;

            if (card.querySelector(`[data-odv2-carga-inline-insert="${def.insertar}"]`)) {
                return;
            }

            const actions = document.createElement("div");
            actions.className = "odv2-carga-inline-actions";
            actions.setAttribute("data-odv2-carga-inline-actions", def.verificar);

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "odv2-carga-inline-insert-btn";
            btn.setAttribute("data-odv2-carga-inline-insert", def.insertar);
            btn.textContent = def.label;

            btn.addEventListener("click", async event => {
                event.preventDefault();
                event.stopPropagation();
                await ejecutarCargaSqlMvc(def.insertar, btn);
            });

            actions.appendChild(btn);

            const header =
                card.querySelector(".odv2-phase-header") ||
                card.querySelector(".odv2-phase-head") ||
                card.querySelector(".odv2-card-head") ||
                card.querySelector("header");

            if (header && header.parentNode) {
                header.parentNode.insertBefore(actions, header.nextSibling);
            } else {
                const firstResult = card.querySelector(".odv2-phase-result, [id^='odv2-result'], .odv2-result");

                if (firstResult && firstResult.parentNode) {
                    firstResult.parentNode.insertBefore(actions, firstResult);
                } else {
                    card.appendChild(actions);
                }
            }
        });
    }

    function odv2CargaInlineSchedule() {
        [100, 300, 700, 1200, 2000].forEach(ms => {
            setTimeout(odv2CargaInlineEnsureButtons, ms);
        });
    }

    document.addEventListener("click", event => {
        const text = String(event.target?.textContent || "").toLowerCase();

        if (
            text.includes("cargar contexto") ||
            text.includes("gestión diaria orion") ||
            text.includes("gestion diaria orion") ||
            text.includes("carga")
        ) {
            odv2CargaInlineSchedule();
        }
    }, true);

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", odv2CargaInlineSchedule);
    } else {
        odv2CargaInlineSchedule();
    }

    const odv2CargaInlineObserver = new MutationObserver(() => {
        if (odv2CargaInlineObserver.__timer) {
            clearTimeout(odv2CargaInlineObserver.__timer);
        }

        odv2CargaInlineObserver.__timer = setTimeout(odv2CargaInlineEnsureButtons, 150);
    });

    if (document.body) {
        odv2CargaInlineObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

/* === ORION_DIARIO_V2_CARGA_SQL_INLINE_CLEAN_END === */


    async function executeWorkflowAction(actionName, button) {
        if (ORION_CARGA_SQL_ACTIONS.has(actionName)) {
            await ejecutarCargaSqlMvc(actionName, button);
            return;
        }

        if (ORION_PROC_ACTIONS.has(actionName)) {
            await ejecutarProcesamientoMvc(actionName, button);
            return;
        }

        if (actionName === "distribuir.preparar") {
            await ejecutarDistribucionMvc(button);
            return;
        }

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

        const metricas = (data.metricas || []).filter(m => String(m.titulo || "").toLowerCase() !== "total orion");

        root.innerHTML = "";

        metricas.forEach(m => {
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

    function renderPie(data) {
        const root = $("#odv2-bars");
        if (!root) return;

        root.innerHTML = "";

        const metricas = (data.metricas || [])
            .filter(m => String(m.titulo || "").toLowerCase() !== "total orion")
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

        const colors = ["#0ea5ff", "#22c55e", "#f59e0b", "#a855f7", "#ef4444", "#14b8a6"];

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
                    <strong>ORION</strong>
                    <span>Distribución</span>
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

        const rutas = getActiveRoutes();

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

    function categoriaDistribucion(texto) {
        const t = String(texto || "").toLowerCase();

        if (t.includes("causal")) return "causales";
        if (t.includes("discador")) return "discador";
        if (t.includes("lote")) return "lotes";

        return "otros";
    }

    function labelCategoria(cat) {
        if (cat === "causales") return "Causales";
        if (cat === "discador") return "Discador";
        if (cat === "lotes") return "Lotes";
        return "Otros";
    }

    function emptyDistCounts() {
        return { causales: 0, discador: 0, lotes: 0, otros: 0 };
    }

    function collectDistributionSummary(container) {
        const totals = emptyDistCounts();
        const selected = emptyDistCounts();

        const checkboxes = Array.from(container.querySelectorAll('input[type="checkbox"]'));

        checkboxes.forEach(cb => {
            const row = cb.closest("tr") || cb.closest("label") || cb.closest("div") || cb.parentElement;

            const text = [
                cb.name,
                cb.value,
                cb.id,
                row ? row.textContent : ""
            ].join(" ");

            const cat = categoriaDistribucion(text);

            totals[cat] += 1;

            if (cb.checked) selected[cat] += 1;
        });

        return {
            totals,
            selected,
            totalGeneral: Object.values(totals).reduce((a, b) => a + b, 0),
            selectedGeneral: Object.values(selected).reduce((a, b) => a + b, 0),
            checkboxCount: checkboxes.length
        };
    }

    function miniPieHtml(counts, title) {
        const values = [
            { key: "causales", label: "Causales", color: "#0ea5ff", value: counts.causales || 0 },
            { key: "discador", label: "Discador", color: "#22c55e", value: counts.discador || 0 },
            { key: "lotes", label: "Lotes", color: "#f59e0b", value: counts.lotes || 0 },
            { key: "otros", label: "Otros", color: "#a855f7", value: counts.otros || 0 }
        ];

        const total = values.reduce((acc, item) => acc + item.value, 0);

        if (total <= 0) {
            return `<div class="odv2-empty">Sin datos para gráfico.</div>`;
        }

        let start = 0;

        const segments = values.map(item => {
            const pct = item.value / total * 100;
            const end = start + pct;
            const segment = `${item.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
            start = end;
            return segment;
        });

        return `
            <div class="odv2-copy-pie-box">
                <div class="odv2-copy-pie" style="background: conic-gradient(${segments.join(", ")});">
                    <div class="odv2-copy-pie-center">
                        <strong>${escapeHtml(title)}</strong>
                    </div>
                </div>
                <div class="odv2-copy-pie-legend">
                    ${values.map(item => `
                        <div class="odv2-copy-pie-row">
                            <i style="background:${item.color}"></i>
                            <span>${item.label}</span>
                            <b>${fmt(item.value)}</b>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    function distributionSummaryTable(summary, copied) {
        const cats = ["causales", "discador", "lotes", "otros"];

        return `
            <table class="odv2-table odv2-copy-summary-table">
                <thead>
                    <tr>
                        <th>Tipo</th>
                        <th>Total encontrados</th>
                        <th>Total seleccionados</th>
                        <th>Total copiados</th>
                    </tr>
                </thead>
                <tbody>
                    ${cats.map(cat => `
                        <tr>
                            <td>${labelCategoria(cat)}</td>
                            <td>${fmt(summary.totals[cat] || 0)}</td>
                            <td>${fmt(summary.selected[cat] || 0)}</td>
                            <td>${fmt(copied[cat] || 0)}</td>
                        </tr>
                    `).join("")}
                    <tr class="odv2-copy-total-row">
                        <td>Total</td>
                        <td>${fmt(summary.totalGeneral || 0)}</td>
                        <td>${fmt(summary.selectedGeneral || 0)}</td>
                        <td>${fmt(Object.values(copied).reduce((a, b) => a + b, 0))}</td>
                    </tr>
                </tbody>
            </table>
        `;
    }

    function appendDistributionControls(actionName) {
        const result = document.getElementById(phaseResultId(actionName));
        if (!result) return;

        const summary = collectDistributionSummary(result);

        if (!summary.checkboxCount) {
            result.insertAdjacentHTML("beforeend", `
                <div class="odv2-copy-box">
                    <div class="odv2-result-warning">
                        No se encontraron casillas de selección en el resultado de Distribuir.
                    </div>
                </div>
            `);

            state.phaseResults[actionName] = result.innerHTML;
            saveState();
            return;
        }

        if (result.querySelector("[data-odv2-copy-selected]")) return;

        const copiedEmpty = emptyDistCounts();

        result.insertAdjacentHTML("beforeend", `
            <div class="odv2-copy-box">
                <div class="odv2-copy-head">
                    <div>
                        <h4>Copiar archivos seleccionados</h4>
                        <p>Seleccione los archivos en la lista generada y presione copiar.</p>
                    </div>
                    <button class="odv2-primary" data-odv2-copy-selected="${escapeHtml(actionName)}">
                        Copiar seleccionados
                    </button>
                </div>

                <div class="odv2-copy-grid">
                    ${miniPieHtml(summary.selected, "Sel.")}
                    <div>${distributionSummaryTable(summary, copiedEmpty)}</div>
                </div>

                <div class="odv2-copy-result" data-odv2-copy-result="${escapeHtml(actionName)}"></div>
            </div>
        `);

        state.phaseResults[actionName] = result.innerHTML;
        saveState();
    }

    function buildDistributionCopyForm(container) {
        collectInputs();

        const form = new FormData();

        form.append("fecha", state.fechaProceso);
        form.append("fecha_proceso", state.fechaProceso);
        form.append("mes_gestion", state.mesGestion);
        form.append("conexion", state.conexion);

        const inputs = Array.from(container.querySelectorAll("input, select, textarea"));

        inputs.forEach(input => {
            const name = input.name;

            if (!name) return;
            if (input.disabled) return;

            if (input.type === "checkbox") {
                if (input.checked) form.append(name, input.value || "on");
                return;
            }

            if (input.type === "radio") {
                if (input.checked) form.append(name, input.value || "on");
                return;
            }

            form.append(name, input.value || "");
        });

        return form;
    }

    async function copyDistributionSelected(actionName) {
        const result = document.getElementById(phaseResultId(actionName));
        if (!result) return;

        const copyResult = result.querySelector(`[data-odv2-copy-result="${actionName}"]`);
        const summaryBefore = collectDistributionSummary(result);

        if (!summaryBefore.selectedGeneral) {
            if (copyResult) {
                copyResult.innerHTML = `<div class="odv2-result-warning">No hay archivos seleccionados para copiar.</div>`;
            }
            return;
        }

        if (copyResult) {
            copyResult.innerHTML = `<div class="odv2-result-loading">Copiando archivos seleccionados...</div>`;
        }

        try {
            const response = await fetch("/accion/distribuir-seleccionados?_=" + Date.now(), {
                method: "POST",
                body: buildDistributionCopyForm(result),
                credentials: "same-origin"
            });

            const html = await response.text();
            const error = !response.ok || looksLikeError(html);
            const copied = error ? emptyDistCounts() : summaryBefore.selected;

            if (copyResult) {
                copyResult.innerHTML = `
                    <div class="odv2-result-toolbar">
                        <strong>Resultado copia seleccionados</strong>
                        <span>HTTP ${response.status}</span>
                    </div>

                    <div class="odv2-copy-grid">
                        ${miniPieHtml(copied, "Cop.")}
                        <div>${distributionSummaryTable(summaryBefore, copied)}</div>
                    </div>

                    <div class="odv2-result-html">${html}</div>
                `;
            }

            setPhaseStatus(actionName, error ? "error" : "success", error ? "Error copia" : "Copiado");

            state.phaseResults[actionName] = result.innerHTML;
            saveState();

            debug(
                error ? "Error copiando seleccionados." : "Archivos seleccionados copiados correctamente.",
                error ? "error" : "success"
            );

        } catch (error) {
            if (copyResult) {
                copyResult.innerHTML = `<div class="odv2-result-error">Error copiando seleccionados: ${escapeHtml(error.message || error)}</div>`;
            }

            setPhaseStatus(actionName, "error", "Error copia");
            debug("Error copiando seleccionados: " + (error.message || error), "error");
        }
    }

    function setupDistributionDelegation() {
        document.addEventListener("click", event => {
            const btn = event.target.closest("[data-odv2-copy-selected]");
            if (!btn) return;

            event.preventDefault();

            const actionName = btn.getAttribute("data-odv2-copy-selected");
            copyDistributionSelected(actionName);
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
        setupDistributionDelegation();
        ensureDebugPanel();

        if (state.contexto) {
            renderContext();
        }

        if (state.estadisticas) {
            renderStats();
        }

        debug("Orion Diario V2 JS V4 cargado. Cargar contexto reinicia la pantalla.", "info");
    }

    document.addEventListener("DOMContentLoaded", init);
})();
