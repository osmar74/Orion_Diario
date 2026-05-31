(function () {
    "use strict";

    function $(selector, root) {
        return (root || document).querySelector(selector);
    }

    function $all(selector, root) {
        return Array.from((root || document).querySelectorAll(selector));
    }

    function cssEscape(value) {
        if (window.CSS && typeof window.CSS.escape === "function") {
            return window.CSS.escape(value);
        }

        return String(value).replace(/"/g, '\\"');
    }

    async function fetchText(url, options) {
        const response = await fetch(url, Object.assign({ credentials: "same-origin" }, options || {}));
        const text = await response.text();

        if (!response.ok) {
            throw new Error(text || ("HTTP " + response.status));
        }

        return text;
    }

    async function fetchJson(url, options) {
        const response = await fetch(url, Object.assign({ credentials: "same-origin" }, options || {}));
        const text = await response.text();

        let data = {};
        try {
            data = JSON.parse(text);
        } catch {
            throw new Error("Respuesta no JSON: " + text.slice(0, 300));
        }

        if (!response.ok) {
            throw new Error(data.error || data.message || ("HTTP " + response.status));
        }

        return data;
    }

    function modal() {
        return document.getElementById("oac-modal");
    }

    function summaryHost() {
        return document.getElementById("oac-summary-host");
    }

    function configHost() {
        return document.getElementById("oac-config-host");
    }

    function setMessage(target, message, className) {
        if (!target) return;

        target.textContent = message;
        target.className = className || target.className;
    }

    function qName(name, root) {
        return (root || document).querySelector('[name="' + cssEscape(name) + '"]');
    }

    function valueByName(name, root) {
        const el = qName(name, root);
        return el ? el.value : "";
    }

    function linesByName(name, root) {
        return valueByName(name, root)
            .split(/\r?\n/)
            .map(x => x.trim())
            .filter(Boolean);
    }

    function sqlBlock(prefix, root) {
        return {
            server: valueByName(prefix + ".server", root),
            port: valueByName(prefix + ".port", root),
            database: valueByName(prefix + ".database", root),
            auth: valueByName(prefix + ".auth", root) || "sql",
            username: valueByName(prefix + ".username", root),
            password: valueByName(prefix + ".password", root)
        };
    }

    function collectConfig(root) {
        return {
            ambiente_activo: ($("#oac-ambiente", root) || {}).value || "local",
            data_root: ($("#oac-data-root", root) || {}).value || "",
            rutas: {
                local: {
                    orion: linesByName("rutas.local.orion", root),
                    aster: linesByName("rutas.local.aster", root)
                },
                remoto: {
                    orion: linesByName("rutas.remoto.orion", root),
                    aster: linesByName("rutas.remoto.aster", root)
                }
            },
            sql: {
                local: {
                    orion: sqlBlock("sql.local.orion", root),
                    aster_api: sqlBlock("sql.local.aster_api", root),
                    gestion_consolidada: sqlBlock("sql.local.gestion_consolidada", root)
                },
                remoto: {
                    orion: sqlBlock("sql.remoto.orion", root),
                    aster_api: sqlBlock("sql.remoto.aster_api", root),
                    gestion_consolidada: sqlBlock("sql.remoto.gestion_consolidada", root)
                }
            }
        };
    }

    async function loadSummary() {
        const host = summaryHost();
        if (!host) return;

        try {
            host.innerHTML = await fetchText("/api/config/global/resumen/html?_=" + Date.now());
            bindOpenButtons();
        } catch (error) {
            setMessage(host, "Error cargando resumen de configuración: " + String(error.message || error), "odv2-result-error");
        }
    }

    async function loadPanel(force) {
        const host = configHost();
        if (!host) return;

        if (!force && host.dataset.loaded === "1") {
            return;
        }

        setMessage(host, "Cargando configuración...", "oac-modal-body");

        try {
            host.innerHTML = await fetchText("/api/config/global/html?_=" + Date.now());
            host.dataset.loaded = "1";
            bindPanelEvents(host);
        } catch (error) {
            setMessage(host, "Error cargando configuración: " + String(error.message || error), "odv2-result-error");
        }
    }

    async function openModal() {
        const m = modal();
        if (!m) return;

        m.classList.remove("hidden");
        m.setAttribute("aria-hidden", "false");
        document.body.classList.add("oac-modal-open");

        await loadPanel(false);
    }

    function closeModal() {
        const m = modal();
        if (!m) return;

        m.classList.add("hidden");
        m.setAttribute("aria-hidden", "true");
        document.body.classList.remove("oac-modal-open");
    }

    function bindOpenButtons() {
        $all(".oac-open-config, #oac-open-config-top, #oac-open-config-sidebar").forEach(btn => {
            if (btn.dataset.oacBound === "1") return;

            btn.dataset.oacBound = "1";
            btn.addEventListener("click", function () {
                openModal();
            });
        });
    }

    function bindCloseButtons() {
        $all("[data-oac-close]").forEach(btn => {
            if (btn.dataset.oacBound === "1") return;

            btn.dataset.oacBound = "1";
            btn.addEventListener("click", closeModal);
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeModal();
            }
        });
    }

    function bindPanelEvents(root) {
        const save = $("#oac-save", root);

        if (save && save.dataset.oacBound !== "1") {
            save.dataset.oacBound = "1";

            save.addEventListener("click", async function () {
                const result = $("#oac-result", root);

                setMessage(result, "Guardando configuración...", "oac-result");

                try {
                    await fetchJson("/api/config/global", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(collectConfig(root))
                    });

                    setMessage(
                        result,
                        "✅ Configuración guardada. Presione Cargar contexto para aplicar los cambios.",
                        "oac-result success"
                    );

                    await loadSummary();

                } catch (error) {
                    setMessage(
                        result,
                        "❌ Error guardando configuración: " + String(error.message || error),
                        "oac-result error"
                    );
                }
            });
        }

        $all("[data-oac-test]", root).forEach(btn => {
            if (btn.dataset.oacBound === "1") return;

            btn.dataset.oacBound = "1";
            btn.addEventListener("click", async function () {
                const conexion = btn.getAttribute("data-oac-test") || "local";
                const result = $("#oac-result", root);

                setMessage(result, "Probando configuración " + conexion.toUpperCase() + "...", "oac-result");

                try {
                    result.innerHTML = await fetchText(
                        "/api/config/probar/html?conexion=" + encodeURIComponent(conexion) + "&_=" + Date.now()
                    );
                } catch (error) {
                    setMessage(
                        result,
                        "❌ Error probando configuración: " + String(error.message || error),
                        "oac-result error"
                    );
                }
            });
        });
    }

    function ensureTopButton() {
        if (document.getElementById("oac-open-config-top")) {
            return;
        }

        const buttons = Array.from(document.querySelectorAll("button"));
        const cargarContexto = buttons.find(btn => /cargar\s+contexto/i.test(btn.textContent || ""));

        if (!cargarContexto || !cargarContexto.parentElement) {
            return;
        }

        const contenedor = cargarContexto.parentElement;

        contenedor.classList.add("oac-top-actions-row");

        const btn = document.createElement("button");
        btn.type = "button";
        btn.id = "oac-open-config-top";
        btn.className = "odv2-secondary oac-top-config-btn";
        btn.textContent = "⚙ Configuración";

        contenedor.insertBefore(btn, cargarContexto);

        btn.addEventListener("click", function () {
            openModal();
        });
    }

    document.addEventListener("DOMContentLoaded", async function () {
        ensureTopButton();
        bindCloseButtons();
        await loadSummary();
    });
})();
