(function () {
    "use strict";

    function $(selector, root) {
        return (root || document).querySelector(selector);
    }

    function $all(selector, root) {
        return Array.from((root || document).querySelectorAll(selector));
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
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

    function valueByName(name) {
        const el = document.querySelector("[name='" + CSS.escape(name) + "']");
        return el ? el.value : "";
    }

    function linesByName(name) {
        return valueByName(name)
            .split(/\r?\n/)
            .map(x => x.trim())
            .filter(Boolean);
    }

    function sqlBlock(prefix) {
        return {
            server: valueByName(prefix + ".server"),
            port: valueByName(prefix + ".port"),
            database: valueByName(prefix + ".database"),
            auth: valueByName(prefix + ".auth") || "sql",
            username: valueByName(prefix + ".username"),
            password: valueByName(prefix + ".password")
        };
    }

    function collectConfig() {
        return {
            ambiente_activo: ($("#oac-ambiente") || {}).value || "local",
            data_root: ($("#oac-data-root") || {}).value || "",
            rutas: {
                local: {
                    orion: linesByName("rutas.local.orion"),
                    aster: linesByName("rutas.local.aster")
                },
                remoto: {
                    orion: linesByName("rutas.remoto.orion"),
                    aster: linesByName("rutas.remoto.aster")
                }
            },
            sql: {
                local: {
                    orion: sqlBlock("sql.local.orion"),
                    aster_api: sqlBlock("sql.local.aster_api"),
                    gestion_consolidada: sqlBlock("sql.local.gestion_consolidada")
                },
                remoto: {
                    orion: sqlBlock("sql.remoto.orion"),
                    aster_api: sqlBlock("sql.remoto.aster_api"),
                    gestion_consolidada: sqlBlock("sql.remoto.gestion_consolidada")
                }
            }
        };
    }

    async function loadPanel() {
        const host = document.getElementById("oac-config-host");
        if (!host) return;

        host.innerHTML = "<div class='odv2-empty'>Cargando configuración...</div>";

        try {
            host.innerHTML = await fetchText("/api/config/global/html?_=" + Date.now());
            bindEvents(host);
        } catch (error) {
            host.innerHTML = "<div class='odv2-result-error'>Error cargando configuración: " + String(error.message || error) + "</div>";
        }
    }

    function bindEvents(root) {
        const save = $("#oac-save", root);

        if (save) {
            save.addEventListener("click", async function () {
                const result = $("#oac-result", root);
                if (result) result.innerHTML = "Guardando configuración...";

                try {
                    await fetchJson("/api/config/global", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(collectConfig())
                    });

                    if (result) {
                        result.innerHTML = "<div class='log-line success'>✅ Configuración guardada. Presione Cargar contexto para aplicar.</div>";
                    }

                } catch (error) {
                    if (result) {
                        result.innerHTML = "<div class='log-line error'>❌ Error guardando configuración: " + String(error.message || error) + "</div>";
                    }
                }
            });
        }

        $all("[data-oac-test]", root).forEach(btn => {
            btn.addEventListener("click", async function () {
                const conexion = btn.getAttribute("data-oac-test") || "local";
                const result = $("#oac-result", root);

                if (result) result.innerHTML = "Probando configuración " + conexion.toUpperCase() + "...";

                try {
                    const html = await fetchText("/api/config/probar/html?conexion=" + encodeURIComponent(conexion) + "&_=" + Date.now());
                    if (result) result.innerHTML = html;
                } catch (error) {
                    if (result) {
                        result.innerHTML = "<div class='log-line error'>❌ Error probando configuración: " + String(error.message || error) + "</div>";
                    }
                }
            });
        });
    }

    document.addEventListener("DOMContentLoaded", loadPanel);
})();
