(function () {
    "use strict";

    const DEFAULT_STATE = {
        conexion: "local",
        fechaProceso: "20260429",
        mesGestion: "abril",
        rutasBase: [],
        contexto: null,
        estadisticas: null
    };

    const state = loadState();

    const $ = (selector) => document.querySelector(selector);

    function loadState() {
        try {
            return { ...DEFAULT_STATE, ...JSON.parse(localStorage.getItem("orion_diario_v2_state") || "{}") };
        } catch {
            return { ...DEFAULT_STATE };
        }
    }

    function saveState() {
        localStorage.setItem("orion_diario_v2_state", JSON.stringify(state));
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

    function collectInputs() {
        state.fechaProceso = $("#odv2-fecha-proceso").value.trim();
        state.mesGestion = $("#odv2-mes-gestion").value.trim();
        saveState();
    }

    function getParams(includeRoutes) {
        collectInputs();

        const params = new URLSearchParams({
            fecha_proceso: state.fechaProceso,
            mes_gestion: state.mesGestion,
            conexion: state.conexion
        });

        if (includeRoutes && state.rutasBase.length) {
            state.rutasBase.forEach(r => params.append("rutas_base", r));
        }

        return params;
    }

    function setActiveConnection() {
        document.querySelectorAll("[data-conn]").forEach(btn => {
            btn.classList.toggle("active", btn.dataset.conn === state.conexion);
        });
    }

    function restoreInputs() {
        $("#odv2-fecha-proceso").value = state.fechaProceso;
        $("#odv2-mes-gestion").value = state.mesGestion;
        setActiveConnection();
    }

    async function loadContext() {
        const res = await fetch("/api/orion-diario-v2/contexto?" + getParams(true).toString());
        state.contexto = await res.json();
        state.estadisticas = null;
        saveState();
        renderContext();
        clearStats();
    }

    async function loadStats() {
        const res = await fetch("/api/orion-diario-v2/estadisticas?" + getParams(true).toString());
        state.estadisticas = await res.json();
        state.contexto = state.estadisticas;
        saveState();
        renderContext();
        renderStats();
    }

    function renderContext() {
        const data = state.contexto;
        if (!data) return;

        $("#odv2-global-status").textContent = data.conexion === "local" ? "Local activo" : "Remoto activo";
        $("#odv2-global-status").classList.add("ok");

        $("#odv2-fecha-proceso").value = data.fecha_proceso || state.fechaProceso;
        $("#odv2-mes-gestion").value = data.mes_gestion || state.mesGestion;

        state.fechaProceso = $("#odv2-fecha-proceso").value;
        state.mesGestion = $("#odv2-mes-gestion").value;

        if (!state.rutasBase.length && Array.isArray(data.rutas_red)) {
            state.rutasBase = data.rutas_red.map(r => r.base);
        }

        renderSidebar(data);
        renderRoutes(data);
        renderLocalServers(data);
        renderPhaseBoard(data);
    }

    function clearStats() {
        $("#odv2-metrics-message").style.display = "block";
        $("#odv2-metrics").innerHTML = "";
        $("#odv2-bars").innerHTML = "";
        $("#odv2-connections").innerHTML = '<div class="odv2-empty">Ejecute el panel estadístico para ver información de conexión.</div>';
    }

    function renderStats() {
        const data = state.estadisticas;
        if (!data) return;

        $("#odv2-metrics-message").style.display = "none";
        renderMetrics(data);
        renderBars(data);
        renderConnections(data);
    }

    function renderSidebar(data) {
        const root = $("#odv2-sidebar-phases");
        root.innerHTML = "";

        data.fases.forEach(f => {
            const div = document.createElement("div");
            div.className = "odv2-phase-mini";
            div.innerHTML = `
                <span><b>${f.codigo}</b>${f.nombre}</span>
                <span class="odv2-badge">${f.badge}</span>
            `;
            root.appendChild(div);
        });
    }

    function renderRoutes(data) {
        const root = $("#odv2-routes");
        root.innerHTML = "";

        data.rutas_red.forEach(r => {
            const div = document.createElement("div");
            div.className = "odv2-route";
            div.innerHTML = `
                <small>${r.nombre}</small>
                <strong>Base:</strong> ${r.base}<br>
                <strong>Mes gestión:</strong> ${r.ruta_mes}
            `;
            root.appendChild(div);
        });

        if (data.rutas_locales) {
            Object.entries(data.rutas_locales).forEach(([k, v]) => {
                const div = document.createElement("div");
                div.className = "odv2-route";
                div.innerHTML = `<small>${k}</small>${v}`;
                root.appendChild(div);
            });
        }

        renderPathsForm();
    }

    function renderLocalServers(data) {
        const root = $("#odv2-local-servers");

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
                            <td>${s.tipo}</td>
                            <td>${s.servidor}</td>
                            <td>${s.base_datos || "--"}</td>
                            <td>${s.uso || "--"}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    function renderPhaseBoard(data) {
        const root = $("#odv2-phase-board");
        root.innerHTML = "";

        data.fases.forEach(f => {
            const item = document.createElement("div");
            item.className = "odv2-phase";
            item.innerHTML = `
                <div class="odv2-phase-head">
                    <span>${f.codigo} — ${f.nombre}</span>
                    <span>${f.badge}</span>
                </div>
                <div class="odv2-phase-body">
                    <div>
                        <strong>${f.grupo}</strong><br>
                        ${f.descripcion}
                    </div>
                    <button class="odv2-run" data-phase="${f.codigo}" data-action="${f.accion}">Ejecutar fase</button>
                </div>
            `;
            root.appendChild(item);
        });

        root.querySelectorAll(".odv2-run").forEach(btn => {
            btn.addEventListener("click", () => {
                alert("Fase " + btn.dataset.phase + " todavía no vinculada en v2. La pantalla actual sigue funcionando.");
            });
        });
    }

    function renderMetrics(data) {
        const root = $("#odv2-metrics");
        root.innerHTML = "";

        data.metricas.forEach(m => {
            const card = document.createElement("div");
            card.className = "odv2-metric";
            card.innerHTML = `
                <small>${m.titulo}</small>
                <strong>${fmt(m.valor)}</strong>
                <span>${m.detalle || ""}</span>
            `;
            root.appendChild(card);
        });
    }

    function renderBars(data) {
        const root = $("#odv2-bars");
        root.innerHTML = "";

        const values = data.metricas
            .map(x => Number(x.valor || 0))
            .filter(x => !Number.isNaN(x));

        const max = Math.max(...values, 1);

        data.metricas.forEach(m => {
            const value = Number(m.valor || 0);
            const pct = Math.max(3, Math.round((value / max) * 100));

            const row = document.createElement("div");
            row.className = "odv2-bar-row";
            row.innerHTML = `
                <label><span>${m.titulo}</span><span>${fmt(m.valor)}</span></label>
                <div class="odv2-bar-track">
                    <div class="odv2-bar-fill" style="width:${pct}%"></div>
                </div>
            `;
            root.appendChild(row);
        });
    }

    function renderConnections(data) {
        const root = $("#odv2-connections");

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
                            <td>${c.proceso}</td>
                            <td>${c.origen}</td>
                            <td>${c.destino}</td>
                            <td>${c.servidor}</td>
                            <td>${c.base_datos}</td>
                            <td>${c.tabla}</td>
                            <td>${c.ruta}</td>
                            <td>${fmt(c.total)}</td>
                            <td>${c.estado}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    function renderPathsForm() {
        const root = $("#odv2-paths-form");
        root.innerHTML = "";

        const rutas = state.rutasBase.length ? state.rutasBase : [
            "\\\\10.24.90.118\\Vencorp\\COBRANZA %\\2024\\Prueba _carga_diaria_Aster_voip\\Orion",
            "Z:\\COBRANZA %\\2024\\Prueba _carga_diaria_Aster_voip\\Orion",
            "D:\\Develop\\ETL\\Nicaragua_Proceso\\unidad_red_orion\\COBRANZA %\\2024\\Prueba _carga_diaria_Aster_voip\\Orion"
        ];

        rutas.forEach((ruta, idx) => {
            const div = document.createElement("div");
            div.className = "odv2-field";
            div.innerHTML = `
                <label>Ruta base ${idx + 1}</label>
                <input data-path-index="${idx}" value="${String(ruta).replaceAll('"', "&quot;")}">
            `;
            root.appendChild(div);
        });
    }

    function setupModal() {
        $("#odv2-edit-paths").addEventListener("click", () => {
            renderPathsForm();
            $("#odv2-paths-modal").classList.add("show");
        });

        $("#odv2-close-modal").addEventListener("click", () => {
            $("#odv2-paths-modal").classList.remove("show");
        });

        $("#odv2-save-paths").addEventListener("click", () => {
            state.rutasBase = Array.from(document.querySelectorAll("[data-path-index]"))
                .map(input => input.value.trim())
                .filter(Boolean);

            saveState();
            $("#odv2-paths-modal").classList.remove("show");
            loadContext();
        });

        $("#odv2-reset-paths").addEventListener("click", () => {
            state.rutasBase = [];
            saveState();
            renderPathsForm();
        });
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

    function init() {
        restoreInputs();

        document.querySelectorAll("[data-conn]").forEach(btn => {
            btn.addEventListener("click", () => {
                state.conexion = btn.dataset.conn;
                saveState();
                setActiveConnection();
                loadContext();
            });
        });

        $("#odv2-load-context").addEventListener("click", loadContext);
        $("#odv2-load-stats").addEventListener("click", loadStats);

        setupModal();
        setupCollapsibles();

        if (state.contexto) {
            renderContext();
        }
    }

    document.addEventListener("DOMContentLoaded", init);
})();
