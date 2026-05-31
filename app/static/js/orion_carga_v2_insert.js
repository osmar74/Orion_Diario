(function () {
    "use strict";

    function getFechaProceso() {
        const input = document.getElementById("odv2-fecha-proceso");
        const value = input && input.value ? input.value.trim() : "";
        return value || "20260429";
    }

    function getConexionActiva(btn) {
        const fromButton = btn.getAttribute("data-conexion");
        if (fromButton) return fromButton;

        const selected = document.querySelector("[data-conexion].active, .active[data-connection]");
        if (selected) {
            return selected.getAttribute("data-conexion") || selected.getAttribute("data-connection") || "local";
        }

        return "local";
    }

    function setHtml(target, html) {
        if (target) {
            target.innerHTML = html;
        }
    }

    function findInsertionPanel(btn) {
        const box = btn.closest(".odv2-carga-sql-box");

        if (!box) return null;

        const details = Array.from(box.querySelectorAll("details"));

        for (const detail of details) {
            const summary = detail.querySelector("summary");
            const text = summary ? summary.textContent.toLowerCase() : "";

            if (text.includes("inserción") || text.includes("insercion")) {
                return detail;
            }
        }

        return null;
    }

    function updateInsertionPanel(btn, html) {
        const detail = findInsertionPanel(btn);

        if (!detail) return;

        const body =
            detail.querySelector(".odv2-carga-sql-original") ||
            detail.querySelector(".odv2-proc-original") ||
            detail;

        body.innerHTML = html;
        detail.open = true;
    }

    async function precheckDuplicados(tipo, conexion, fecha) {
        const params = new URLSearchParams();
        params.set("tipo", tipo);
        params.set("conexion", conexion);
        params.set("fecha", fecha);
        params.set("fecha_proceso", fecha);

        const response = await fetch("/api/orion-diario-v2/carga/precheck?" + params.toString() + "&_=" + Date.now(), {
            credentials: "same-origin"
        });

        return await response.json();
    }

    async function insertarDatos(tipo, conexion, fecha) {
        const formData = new FormData();
        formData.append("tipo", tipo);
        formData.append("conexion", conexion);
        formData.append("fecha", fecha);
        formData.append("fecha_proceso", fecha);

        const response = await fetch("/accion/insertar-datos?_=" + Date.now(), {
            method: "POST",
            credentials: "same-origin",
            body: formData
        });

        const html = await response.text();

        return {
            ok: response.ok,
            status: response.status,
            html: html
        };
    }

    document.addEventListener("click", async function (event) {
        const btn = event.target.closest("[data-orion-carga-v2-insert='1']");

        if (!btn) return;

        event.preventDefault();
        event.stopPropagation();

        const tipo = btn.getAttribute("data-tipo") || "";
        const conexion = getConexionActiva(btn);
        const fecha = getFechaProceso();
        const targetId = btn.getAttribute("data-target");
        const target = targetId ? document.getElementById(targetId) : null;

        if (!tipo) {
            const html = "<div class='odv2-result-error'>❌ No se pudo determinar el tipo de carga.</div>";
            // Resultado visual solo en el panel "Resultado de inserción".
            updateInsertionPanel(btn, html);
            return;
        }

        const originalText = btn.textContent;

        btn.disabled = true;
        btn.textContent = "Validando...";
        // No escribir resultado dentro de la verificación para evitar duplicidad.
        updateInsertionPanel(btn, "<div class='odv2-result-loading'>Validando duplicados para la fecha " + fecha + "...</div>");

        try {
            const precheck = await precheckDuplicados(tipo, conexion, fecha);

            if (!precheck || !precheck.ok) {
                const html =
                    "<div class='odv2-result-error'>❌ No se pudo validar duplicados: " +
                    ((precheck && precheck.mensaje) ? precheck.mensaje : "respuesta inválida") +
                    "</div>";

                // Resultado visual solo en el panel "Resultado de inserción".
                updateInsertionPanel(btn, html);
                btn.disabled = false;
                btn.textContent = originalText;
                return;
            }

            if (Number(precheck.registros_existentes || 0) > 0) {
                const html =
                    "<div class='odv2-result-warning'>⚠️ Ya existen " +
                    precheck.registros_existentes +
                    " registros para la fecha " +
                    (precheck.fecha_sql || fecha) +
                    ". Inserción bloqueada para evitar duplicados.</div>";

                // Resultado visual solo en el panel "Resultado de inserción".
                updateInsertionPanel(btn, html);
                btn.disabled = false;
                btn.textContent = originalText;
                return;
            }

            btn.textContent = "Insertando...";
            // Resultado visual solo en el panel "Resultado de inserción".
            updateInsertionPanel(btn, "<div class='odv2-result-loading'>Insertando datos en SQL Server...</div>");

            const result = await insertarDatos(tipo, conexion, fecha);

            // Resultado visual solo en el panel "Resultado de inserción".
            updateInsertionPanel(btn, result.html);

            const lower = String(result.html || "").toLowerCase();
            const failed = lower.includes("❌") || lower.includes("error") || lower.includes("duplicada bloqueada");

            if (failed) {
                btn.disabled = false;
                btn.textContent = originalText;
            } else {
                btn.textContent = "Inserción ejecutada";
                btn.disabled = true;
            }

        } catch (error) {
            const html = "<div class='odv2-result-error'>❌ Error insertando datos: " + error + "</div>";

            // Resultado visual solo en el panel "Resultado de inserción".
            updateInsertionPanel(btn, html);

            btn.disabled = false;
            btn.textContent = originalText;
        }
    }, true);
})();
