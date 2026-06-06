(function () {
    "use strict";

    const UI_VERSION = "integral_v2_c_archivo_d_comparar_v1";
    const STORE_PREFIX = "integral_diario_v2_estado__";

    const endpointMap = {
        "contexto": "fase-contexto",
        "preparar-entorno": "preparar-entorno",
        "entidades": "entidades",
        "gestionar-archivo": "gestionar-archivo",
        "comparar-entidades": "comparar-entidades",
        "sincronizar-origen": "sincronizar-origen",
        "cargar-tabla-inicial": "cargar-tabla-inicial",
        "ejecutar-sql": "ejecutar-sql",
        "generar-oficiales": "generar-oficiales",
        "cargar-vencorp-cubo": "cargar-vencorp-cubo",
        "copiar-validar-final": "copiar-validar-final"
    };

    function byId(id) { return document.getElementById(id); }
    function qsa(selector, root) { return Array.from((root || document).querySelectorAll(selector)); }
    function closest(target, selector) { return target && target.closest ? target.closest(selector) : null; }

    function clearOldUiStateIfNeeded() {
        const versionKey = "integral_diario_v2_ui_version";
        const current = localStorage.getItem(versionKey);
        if (current === UI_VERSION) return;

        Object.keys(localStorage).forEach(function (key) {
            if (
                key.startsWith(STORE_PREFIX) ||
                key.startsWith("integral_v2_collapse_") ||
                key.startsWith("integral_v2_collapse_fixed_")
            ) {
                localStorage.removeItem(key);
            }
        });

        localStorage.setItem(versionKey, UI_VERSION);
    }

    function formData() {
        const form = byId("integralV2Form");
        return form ? new FormData(form) : new FormData();
    }

    function templateHtml(id) {
        const template = byId(id);
        return template ? template.innerHTML : "";
    }

    function loadingHtml() {
        return templateHtml("integralV2LoadingTemplate") ||
            '<div class="integral-loading">Procesando solicitud...</div>';
    }

    function errorHtml() {
        return templateHtml("integralV2ErrorComTemplate") ||
            '<div class="integral-alert error"><strong>Sin conexión.</strong> No fue posible comunicarse con el servidor.</div>';
    }

    function normalizedState(estado) {
        return String(estado || "Pendiente").toLowerCase().replace(/\s+/g, "-");
    }

    function setConnection(conexion) {
        const hidden = byId("integralConexion");
        const sidebarAmbiente = byId("integralSidebarAmbiente");
        if (hidden) hidden.value = conexion;

        qsa(".intv2-conn-btn").forEach(function (btn) {
            btn.classList.toggle("active", btn.dataset.integralConn === conexion);
        });

        if (sidebarAmbiente) {
            sidebarAmbiente.textContent = conexion === "remoto" ? "REMOTO - Producción" : "LOCAL - Pruebas";
        }

        saveState();
    }

    function setFaseEstado(fase, estado) {
        if (!fase) return;
        const normalized = normalizedState(estado);
        const card = byId("integral-central-fase-" + String(fase).toLowerCase());

        if (card) {
            card.classList.remove("pendiente", "proceso", "correcto", "completado", "revisar", "error");
            card.classList.add(normalized);
            const status = card.querySelector(".integral-central-fase-status");
            if (status) status.textContent = estado;
        }

        qsa('.integral-fase-sidebar-row[data-integral-fase="' + fase + '"] .integral-fase-sidebar-status')
            .forEach(function (el) {
                el.textContent = estado;
                el.className = "integral-fase-sidebar-status " + normalized;
            });
    }

    function setFaseResult(fase, html) {
        const target = byId("integral-fase-result-" + String(fase).toLowerCase());
        if (target) target.innerHTML = html;
    }

    async function postHtml(endpoint) {
        const response = await fetch("/accion/integral-diario-v2/" + endpoint, {
            method: "POST",
            body: formData(),
            credentials: "same-origin"
        });
        return { ok: response.ok, html: await response.text() };
    }

    async function cargarResumenContexto() {
        const summary = byId("integralContextSummary");
        if (!summary) return;
        const result = await postHtml("contexto");
        summary.innerHTML = result.html;
    }

    function resetForContext() {
        qsa(".integral-central-fase-card").forEach(function (card) {
            const fase = card.id.replace("integral-central-fase-", "").toUpperCase();
            const target = byId("integral-fase-result-" + fase.toLowerCase());
            card.classList.remove("proceso", "correcto", "completado", "revisar", "error", "intv2-phase-collapsed");
            card.classList.add("pendiente");
            const status = card.querySelector(".integral-central-fase-status");
            if (status) status.textContent = "Pendiente";
            if (target) target.innerHTML = "Resultado pendiente.";
        });

        qsa(".integral-fase-sidebar-row").forEach(function (row) {
            const status = row.querySelector(".integral-fase-sidebar-status");
            if (status) {
                status.textContent = "Pendiente";
                status.className = "integral-fase-sidebar-status pendiente";
            }
        });
    }

    async function ejecutarFase(fase, action) {
        const endpoint = endpointMap[action] || action;
        if (action === "contexto") resetForContext();

        setFaseEstado(fase, "Proceso");
        setFaseResult(fase, loadingHtml());

        try {
            if (action === "contexto") await cargarResumenContexto();
            const result = await postHtml(endpoint);
            setFaseResult(fase, result.html);
            setFaseEstado(fase, result.ok ? "Correcto" : "Revisar");
            saveState();
            restoreCollapseStates();
        } catch (error) {
            setFaseResult(fase, errorHtml());
            setFaseEstado(fase, "Error");
            saveState();
        }
    }

    function collapseKeyFor(card) {
        return card.getAttribute("data-collapse-key") ||
               card.getAttribute("data-phase-collapse-key") ||
               card.id ||
               card.textContent.trim().slice(0, 45);
    }

    function keyCollapse(card) { return "integral_v2_collapse_" + collapseKeyFor(card); }

    function toggleStandardCard(card) {
        const collapsed = card.classList.toggle("intv2-collapsed");
        localStorage.setItem(keyCollapse(card), collapsed ? "1" : "0");
    }

    function togglePhaseCard(card) {
        const collapsed = card.classList.toggle("intv2-phase-collapsed");
        localStorage.setItem(keyCollapse(card), collapsed ? "1" : "0");
    }

    function restoreCollapseStates(root) {
        const base = root || document;

        qsa(".intv2-collapsible, .integral-result-section", base).forEach(function (card) {
            const stored = localStorage.getItem(keyCollapse(card));
            if (stored === "1") card.classList.add("intv2-collapsed");
            else if (stored === "0") card.classList.remove("intv2-collapsed");
        });

        qsa(".integral-central-fase-card", base).forEach(function (card) {
            const stored = localStorage.getItem(keyCollapse(card));
            if (stored === "1") card.classList.add("intv2-phase-collapsed");
            else if (stored === "0") card.classList.remove("intv2-phase-collapsed");

            const head = card.querySelector(".integral-central-fase-head");
            if (head) {
                head.setAttribute("role", "button");
                head.setAttribute("tabindex", "0");
            }
        });
    }

    function saveState() {
        try {
            const htmlIds = ["integralContextSummary", "integralSidebarFasesContainer", "integralV2Resultado"];
            const valueIds = ["integralFecha", "integralMesGestion", "integralConexion", "integralTipo", "integralEntidadesCsv", "integralArchivo"];

            htmlIds.forEach(function (id) {
                const el = byId(id);
                if (el) localStorage.setItem(STORE_PREFIX + id + "_html", el.innerHTML || "");
            });

            valueIds.forEach(function (id) {
                const el = byId(id);
                if (el) localStorage.setItem(STORE_PREFIX + id + "_value", el.value || "");
            });
        } catch (error) {
            console.warn("No se pudo guardar estado Integral", error);
        }
    }

    function restoreState() {
        const htmlIds = ["integralContextSummary", "integralSidebarFasesContainer", "integralV2Resultado"];
        const valueIds = ["integralFecha", "integralMesGestion", "integralConexion", "integralTipo", "integralEntidadesCsv", "integralArchivo"];

        htmlIds.forEach(function (id) {
            const el = byId(id);
            const html = localStorage.getItem(STORE_PREFIX + id + "_html");
            if (el && html) el.innerHTML = html;
        });

        valueIds.forEach(function (id) {
            const el = byId(id);
            const value = localStorage.getItem(STORE_PREFIX + id + "_value");
            if (el && value !== null) el.value = value;
        });

        const conn = byId("integralConexion");
        setConnection(conn ? conn.value : "local");
        restoreCollapseStates();
    }

    function setupStateObservers() {
        ["integralFecha", "integralMesGestion", "integralEntidadesCsv", "integralArchivo"].forEach(function (id) {
            const el = byId(id);
            if (!el) return;
            el.addEventListener("input", saveState);
            el.addEventListener("change", saveState);
        });
    }

    function handleClick(event) {
        const target = event.target;

        const phaseButton = closest(target, ".integral-central-fase-btn[data-integral-action]");
        if (phaseButton) {
            event.preventDefault();
            event.stopPropagation();
            ejecutarFase(phaseButton.dataset.integralFase, phaseButton.dataset.integralAction);
            return;
        }

        const loadContext = closest(target, "#integralLoadContext");
        if (loadContext) {
            event.preventDefault();
            event.stopPropagation();
            ejecutarFase("A", "contexto");
            return;
        }

        const connButton = closest(target, ".intv2-conn-btn");
        if (connButton) {
            event.preventDefault();
            event.stopPropagation();
            setConnection(connButton.dataset.integralConn || "local");
            return;
        }

        const aplicarEntidades = closest(target, "#integralAplicarEntidades");
        if (aplicarEntidades) {
            event.preventDefault();
            event.stopPropagation();
            const values = qsa(".integral-entidad-check:checked").map(function (item) { return item.value; });
            const input = byId("integralEntidadesCsv");
            if (input) input.value = values.join(",");
            saveState();
            return;
        }

        const usarArchivo = closest(target, ".integral-usar-archivo");
        if (usarArchivo) {
            event.preventDefault();
            event.stopPropagation();
            const input = byId("integralArchivo");
            if (input) input.value = usarArchivo.dataset.ruta || "";
            saveState();
            return;
        }

        const standardHead = closest(target, ".intv2-card-head, .integral-result-section-head");
        if (standardHead) {
            const card = closest(standardHead, ".intv2-collapsible, .integral-result-section");
            if (card) {
                event.preventDefault();
                event.stopPropagation();
                toggleStandardCard(card);
                return;
            }
        }

        const phaseHead = closest(target, ".integral-central-fase-head");
        if (phaseHead) {
            const card = closest(phaseHead, ".integral-central-fase-card");
            if (card) {
                event.preventDefault();
                event.stopPropagation();
                togglePhaseCard(card);
            }
        }
    }

    function handleKeydown(event) {
        if (event.key !== "Enter" && event.key !== " ") return;

        const phaseHead = closest(event.target, ".integral-central-fase-head");
        if (phaseHead) {
            event.preventDefault();
            const card = closest(phaseHead, ".integral-central-fase-card");
            if (card) togglePhaseCard(card);
            return;
        }

        const standardHead = closest(event.target, ".intv2-card-head, .integral-result-section-head");
        if (standardHead) {
            event.preventDefault();
            const card = closest(standardHead, ".intv2-collapsible, .integral-result-section");
            if (card) toggleStandardCard(card);
        }
    }

    function observeDynamicResults() {
        const result = byId("integralV2Resultado");
        if (!result || !window.MutationObserver) return;

        const observer = new MutationObserver(function () { restoreCollapseStates(result); });
        observer.observe(result, { childList: true, subtree: true });
    }

    function init() {
        clearOldUiStateIfNeeded();
        restoreState();
        setupStateObservers();
        restoreCollapseStates();
        observeDynamicResults();
        document.addEventListener("click", handleClick, false);
        document.addEventListener("keydown", handleKeydown, false);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();
/* === Integral v2: aplicar entidades comparadas seleccionadas === */
(function () {
    "use strict";

    const STORE_PREFIX = "integral_diario_v2_estado__";

    function qsa(selector, root) {
        return Array.from((root || document).querySelectorAll(selector));
    }

    function byId(id) {
        return document.getElementById(id);
    }

    function toInt(value) {
        const n = parseInt(String(value || "0").replace(",", "").trim(), 10);
        return Number.isFinite(n) ? n : 0;
    }

    function saveSelectedEntitiesCsv(items) {
        const input = byId("integralEntidadesCsv");
        if (input) {
            input.value = items.map(function (item) { return item.entidad; }).join(",");
            input.dispatchEvent(new Event("change", { bubbles: true }));
        }
    }

    function persistirEstadoVisible() {
        try {
            const htmlIds = [
                "integralContextSummary",
                "integralSidebarFasesContainer",
                "integralV2Resultado"
            ];

            const valueIds = [
                "integralFecha",
                "integralMesGestion",
                "integralConexion",
                "integralTipo",
                "integralEntidadesCsv",
                "integralArchivo"
            ];

            htmlIds.forEach(function (id) {
                const el = byId(id);
                if (el) {
                    localStorage.setItem(STORE_PREFIX + id + "_html", el.innerHTML || "");
                }
            });

            valueIds.forEach(function (id) {
                const el = byId(id);
                if (el) {
                    localStorage.setItem(STORE_PREFIX + id + "_value", el.value || "");
                }
            });
        } catch (error) {
            console.warn("No se pudo persistir estado luego de aplicar entidades.", error);
        }
    }

    function setFaseDEstadoCorrecto() {
        const card = byId("integral-central-fase-d");

        if (card) {
            card.classList.remove("pendiente", "proceso", "revisar", "error", "completado");
            card.classList.add("correcto");

            const status = card.querySelector(".integral-central-fase-status");
            if (status) {
                status.textContent = "Correcto";
            }
        }

        qsa('.integral-fase-sidebar-row[data-integral-fase="D"] .integral-fase-sidebar-status')
            .forEach(function (el) {
                el.textContent = "Correcto";
                el.className = "integral-fase-sidebar-status correcto";
            });

        persistirEstadoVisible();
    }

    async function aplicarEntidadesComparadas(event) {
        const button = event.target.closest("#integralAplicarEntidadesComparadas");
        if (!button) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        const checks = qsa(".integral-entidad-compare-check:checked");
        const items = checks.map(function (check) {
            return {
                entidad: check.dataset.entidad || check.value || "",
                reg_sql: toInt(check.dataset.regSql),
                reg_archivo: toInt(check.dataset.regArchivo),
                diferencia: toInt(check.dataset.diferencia),
                estado: check.dataset.estado || ""
            };
        }).filter(function (item) {
            return item.entidad;
        });

        saveSelectedEntitiesCsv(items);

        const formData = new FormData();
        formData.append("entidades_json", JSON.stringify(items));

        const target = byId("integralEntidadesSeleccionadasResultado");
        if (target) {
            target.innerHTML = '<div class="integral-loading">Aplicando entidades seleccionadas...</div>';
        }

        try {
            const response = await fetch("/accion/integral-diario-v2/aplicar-entidades-comparadas", {
                method: "POST",
                body: formData,
                credentials: "same-origin"
            });

            const html = await response.text();

            if (target) {
                target.innerHTML = html;
            }

            if (response.ok && items.length > 0) {
                setFaseDEstadoCorrecto();
            } else {
                persistirEstadoVisible();
            }
        } catch (error) {
            if (target) {
                target.innerHTML = '<div class="integral-alert error"><strong>Error.</strong> No se pudo aplicar la selección.</div>';
            }
            persistirEstadoVisible();
        }
    }

    document.addEventListener("click", aplicarEntidadesComparadas, true);
})();

/* === Integral v2: eliminar duplicidad Fase E === */
(function () {
    "use strict";

    const STORE_PREFIX = "integral_diario_v2_estado__";

    function byId(id) {
        return document.getElementById(id);
    }

    function persistirEstadoVisible() {
        try {
            ["integralContextSummary", "integralSidebarFasesContainer", "integralV2Resultado"].forEach(function (id) {
                const el = byId(id);
                if (el) {
                    localStorage.setItem(STORE_PREFIX + id + "_html", el.innerHTML || "");
                }
            });

            ["integralFecha", "integralMesGestion", "integralConexion", "integralTipo", "integralEntidadesCsv", "integralArchivo"].forEach(function (id) {
                const el = byId(id);
                if (el) {
                    localStorage.setItem(STORE_PREFIX + id + "_value", el.value || "");
                }
            });
        } catch (error) {
            console.warn("No se pudo persistir estado luego de eliminar duplicidad.", error);
        }
    }

    function formDataIntegral() {
        const form = byId("integralV2Form");
        return form ? new FormData(form) : new FormData();
    }

    async function eliminarDuplicidadFaseE(event) {
        const button = event.target.closest("#integralEliminarDuplicadosFaseE");
        if (!button) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        const ok = window.confirm(
            "Se eliminarán los datos existentes de Aster_Integral_Api.integral.comentarios " +
            "para la fecha de proceso y entidades seleccionadas. ¿Deseas continuar?"
        );

        if (!ok) {
            return;
        }

        const target = byId("integralFaseEDuplicidadAccionResultado");
        if (target) {
            target.innerHTML = '<div class="integral-loading">Eliminando datos existentes...</div>';
        }

        try {
            const response = await fetch("/accion/integral-diario-v2/eliminar-duplicidad-fase-e", {
                method: "POST",
                body: formDataIntegral(),
                credentials: "same-origin"
            });

            const html = await response.text();

            if (target) {
                target.innerHTML = html;
            }

            persistirEstadoVisible();
        } catch (error) {
            if (target) {
                target.innerHTML = '<div class="integral-alert error"><strong>Error.</strong> No se pudo eliminar la duplicidad.</div>';
            }

            persistirEstadoVisible();
        }
    }

    document.addEventListener("click", eliminarDuplicidadFaseE, true);
})();

/* === Integral v2: eliminar duplicidad Fase F === */
(function () {
    "use strict";
    const STORE_PREFIX = "integral_diario_v2_estado__";
    function byId(id) { return document.getElementById(id); }
    function persistirEstadoVisible() {
        try {
            ["integralContextSummary", "integralSidebarFasesContainer", "integralV2Resultado"].forEach(function (id) {
                const el = byId(id);
                if (el) localStorage.setItem(STORE_PREFIX + id + "_html", el.innerHTML || "");
            });
            ["integralFecha", "integralMesGestion", "integralConexion", "integralTipo", "integralEntidadesCsv", "integralArchivo"].forEach(function (id) {
                const el = byId(id);
                if (el) localStorage.setItem(STORE_PREFIX + id + "_value", el.value || "");
            });
        } catch (error) { console.warn("No se pudo persistir estado luego de eliminar duplicidad F.", error); }
    }
    function formDataIntegral() {
        const form = byId("integralV2Form");
        return form ? new FormData(form) : new FormData();
    }
    async function eliminarDuplicidadFaseF(event) {
        const button = event.target.closest("#integralEliminarDuplicadosFaseF");
        if (!button) return;
        event.preventDefault();
        event.stopPropagation();
        const ok = window.confirm("Se eliminarán los datos existentes de la tabla inicial para la fecha de proceso. ¿Deseas continuar?");
        if (!ok) return;
        const target = byId("integralFaseFDuplicidadAccionResultado");
        if (target) target.innerHTML = '<div class="integral-loading">Eliminando datos existentes...</div>';
        try {
            const response = await fetch("/accion/integral-diario-v2/eliminar-duplicidad-fase-f", { method: "POST", body: formDataIntegral(), credentials: "same-origin" });
            const html = await response.text();
            if (target) target.innerHTML = html;
            persistirEstadoVisible();
        } catch (error) {
            if (target) target.innerHTML = '<div class="integral-alert error"><strong>Error.</strong> No se pudo eliminar la duplicidad.</div>';
            persistirEstadoVisible();
        }
    }
    document.addEventListener("click", eliminarDuplicidadFaseF, true);
})();

/* === Integral v2 bloque C-D: estado archivo y entidades seleccionadas === */
(function () {
    "use strict";
    const STORE_PREFIX = "integral_diario_v2_estado__";
    function byId(id) { return document.getElementById(id); }
    function qsa(selector, root) { return Array.from((root || document).querySelectorAll(selector)); }
    function toInt(value) { const n = parseInt(String(value || "0").replace(",", "").trim(), 10); return Number.isFinite(n) ? n : 0; }
    function ensureHiddenInput(id, name) {
        let input = byId(id); const form = byId("integralV2Form");
        if (!input && form) { input = document.createElement("input"); input.type = "hidden"; input.id = id; input.name = name; form.appendChild(input); }
        return input;
    }
    function persistirEstadoVisible() {
        try {
            ["integralContextSummary", "integralSidebarFasesContainer", "integralV2Resultado"].forEach(function (id) { const el = byId(id); if (el) localStorage.setItem(STORE_PREFIX + id + "_html", el.innerHTML || ""); });
            ["integralFecha", "integralMesGestion", "integralConexion", "integralTipo", "integralEntidadesCsv", "integralArchivo"].forEach(function (id) { const el = byId(id); if (el) localStorage.setItem(STORE_PREFIX + id + "_value", el.value || ""); });
        } catch (error) { console.warn("No se pudo persistir estado Integral v2.", error); }
    }
    function capturarArchivoFaseC() {
        const source = byId("integralArchivoSeleccionadoPorFaseC"); if (!source || !source.value) return;
        const inputA = ensureHiddenInput("integralArchivo", "archivo"); if (inputA) inputA.value = source.value;
        persistirEstadoVisible();
    }
    function capturarEntidadesSeleccionadas() {
        const source = byId("integralEntidadesSeleccionadasCsv"); if (!source || !source.value) return;
        const input = ensureHiddenInput("integralEntidadesCsv", "entidades_csv"); if (input) input.value = source.value;
        persistirEstadoVisible();
    }
    function setFaseDEstadoCorrecto() {
        const card = byId("integral-central-fase-d");
        if (card) { card.classList.remove("pendiente", "proceso", "revisar", "error", "completado"); card.classList.add("correcto"); const status = card.querySelector(".integral-central-fase-status"); if (status) status.textContent = "Correcto"; }
        qsa('.integral-fase-sidebar-row[data-integral-fase="D"] .integral-fase-sidebar-status').forEach(function (el) { el.textContent = "Correcto"; el.className = "integral-fase-sidebar-status correcto"; });
    }
    async function aplicarEntidadesComparadas(event) {
        const button = event.target.closest("#integralAplicarEntidadesComparadas"); if (!button) return;
        event.preventDefault(); event.stopPropagation();
        const checks = qsa(".integral-entidad-compare-check:checked");
        const items = checks.map(function (check) { return { entidad: check.dataset.entidad || check.value || "", reg_sql: toInt(check.dataset.regSql), reg_archivo: toInt(check.dataset.regArchivo), diferencia: toInt(check.dataset.diferencia), estado: check.dataset.estado || "" }; }).filter(function (item) { return item.entidad; });
        const input = ensureHiddenInput("integralEntidadesCsv", "entidades_csv"); if (input) input.value = items.map(function (item) { return item.entidad; }).join(",");
        const formData = new FormData(); formData.append("entidades_json", JSON.stringify(items));
        const target = byId("integralEntidadesSeleccionadasResultado"); if (target) target.innerHTML = '<div class="integral-loading">Aplicando entidades seleccionadas...</div>';
        try {
            const response = await fetch("/accion/integral-diario-v2/aplicar-entidades-comparadas", { method: "POST", body: formData, credentials: "same-origin" });
            const html = await response.text(); if (target) target.innerHTML = html;
            capturarEntidadesSeleccionadas(); if (response.ok && items.length > 0) setFaseDEstadoCorrecto(); persistirEstadoVisible();
        } catch (error) { if (target) target.innerHTML = '<div class="integral-alert error"><strong>Error.</strong> No se pudo aplicar la selección.</div>'; persistirEstadoVisible(); }
    }
    const observer = new MutationObserver(function () { capturarArchivoFaseC(); capturarEntidadesSeleccionadas(); });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    document.addEventListener("click", aplicarEntidadesComparadas, true);
})();

/* === Integral v2 Bloque 2 E: eliminar duplicidad === */
(function () {
    "use strict";

    function byId(id) { return document.getElementById(id); }

    function formDataIntegral() {
        const form = byId("integralV2Form");
        return form ? new FormData(form) : new FormData();
    }

    document.addEventListener("click", async function (event) {
        const btn = event.target.closest("#integralEliminarDuplicadosFaseE");
        if (!btn) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        const ok = window.confirm("Se eliminarán datos existentes de la fecha de proceso. ¿Deseas continuar?");
        if (!ok) {
            return;
        }

        const target = byId("integralFaseEDuplicidadAccionResultado");
        if (target) {
            target.innerHTML = '<div class="integral-loading">Eliminando duplicidad Fase E...</div>';
        }

        try {
            const response = await fetch("/accion/integral-diario-v2/eliminar-duplicidad-fase-e", {
                method: "POST",
                body: formDataIntegral(),
                credentials: "same-origin"
            });
            const html = await response.text();
            if (target) {
                target.innerHTML = html;
            }
        } catch (error) {
            if (target) {
                target.innerHTML = '<div class="integral-alert error"><strong>Error.</strong> No se pudo eliminar la duplicidad.</div>';
            }
        }
    }, true);
})();

/* === Integral v2 Fase F: eliminar duplicidad === */
(function () {
    "use strict";

    function byId(id) { return document.getElementById(id); }

    function formDataIntegral() {
        const form = byId("integralV2Form");
        return form ? new FormData(form) : new FormData();
    }

    document.addEventListener("click", async function (event) {
        const btn = event.target.closest("#integralEliminarDuplicadosFaseF");
        if (!btn) { return; }

        event.preventDefault();
        event.stopPropagation();

        const ok = window.confirm("Se eliminarán datos existentes de la fecha de proceso. ¿Deseas continuar?");
        if (!ok) { return; }

        const target = byId("integralFaseFDuplicidadAccionResultado");
        if (target) {
            target.innerHTML = '<div class="integral-loading">Eliminando duplicidad Fase F...</div>';
        }

        try {
            const response = await fetch("/accion/integral-diario-v2/eliminar-duplicidad-fase-f", {
                method: "POST",
                body: formDataIntegral(),
                credentials: "same-origin"
            });
            const html = await response.text();
            if (target) { target.innerHTML = html; }
        } catch (error) {
            if (target) {
                target.innerHTML = '<div class="integral-alert error"><strong>Error.</strong> No se pudo eliminar la duplicidad.</div>';
            }
        }
    }, true);
})();

/* === Integral v2 Fase I: eliminar duplicidad Vencorp === */
(function () {
    "use strict";

    function byId(id) { return document.getElementById(id); }

    function formDataIntegral() {
        const form = byId("integralV2Form");
        return form ? new FormData(form) : new FormData();
    }

    document.addEventListener("click", async function (event) {
        const btn = event.target.closest("#integralEliminarDuplicadosFaseI");
        if (!btn) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        const ok = window.confirm("Se eliminarán datos existentes de Vencorp_Integral para la fecha/mes del proceso. ¿Deseas continuar?");
        if (!ok) {
            return;
        }

        const target = byId("integralFaseIDuplicidadAccionResultado");
        if (target) {
            target.innerHTML = '<div class="integral-loading">Eliminando duplicidad Fase I...</div>';
        }

        try {
            const response = await fetch("/accion/integral-diario-v2/eliminar-duplicidad-fase-i", {
                method: "POST",
                body: formDataIntegral(),
                credentials: "same-origin"
            });
            const html = await response.text();
            if (target) {
                target.innerHTML = html;
            }
        } catch (error) {
            if (target) {
                target.innerHTML = '<div class="integral-alert error"><strong>Error.</strong> No se pudo eliminar la duplicidad.</div>';
            }
        }
    }, true);
})();
