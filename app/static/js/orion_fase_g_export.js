(function () {
    "use strict";

    function getById(id) {
        return document.getElementById(id);
    }

    function findPanelFromTrigger(trigger) {
        let node = trigger || null;

        while (node && node !== document.body) {
            if (node.querySelector) {
                const hasTemp = node.querySelector("#cons-temp-id");
                const hasChecks = node.querySelector('input[name="descripcion"]');

                if (hasTemp && hasChecks) {
                    return node;
                }
            }

            node = node.parentElement;
        }

        return null;
    }

    function getResultadoPanel(trigger) {
        return (
            findPanelFromTrigger(trigger) ||
            getById("panel-consolidado-resultado") ||
            getById("odv2-phase-result-consolidado-gestion-consultar") ||
            document.querySelector("[data-action='consolidado.gestion.consultar'] .odv2-result") ||
            document.querySelector(".odv2-phase-card[data-action='consolidado.gestion.consultar']")
        );
    }

    function normalizarFecha(value) {
        let raw = String(value || "").trim().replace(/\//g, "-");

        if (/^\d{8}$/.test(raw)) {
            return raw.slice(0, 4) + "-" + raw.slice(4, 6) + "-" + raw.slice(6, 8);
        }

        return raw;
    }

    function fechaProceso() {
        const input =
            getById("odv2-fecha-proceso") ||
            document.querySelector("[name='fecha_proceso']") ||
            document.querySelector("[name='fecha']");

        const value = input && input.value ? input.value.trim() : "";
        return normalizarFecha(value || "2026-04-29");
    }

    function fechaProcesoCompacta() {
        return fechaProceso().replace(/\D/g, "");
    }

    function mesesGestion() {
        const compacta = fechaProcesoCompacta();

        if (compacta.length >= 6) {
            return compacta.slice(0, 6);
        }

        return "";
    }

    function conexionActiva() {
        const activo =
            document.querySelector("[data-conexion].active") ||
            document.querySelector("[data-connection].active") ||
            document.querySelector(".odv2-connection.active");

        if (activo) {
            return (
                activo.getAttribute("data-conexion") ||
                activo.getAttribute("data-connection") ||
                "local"
            );
        }

        return "local";
    }

    function htmlError(msg) {
        return "<div class='log-line error'>❌ " + String(msg || "Error") + "</div>";
    }

    function htmlLoading(msg) {
        return "<div class='log-line warning'>⏳ " + String(msg || "Procesando...") + "</div>";
    }

    function selectedDescriptions(panel) {
        return Array.from(panel.querySelectorAll('input[name="descripcion"]:checked'))
            .map(function (item) {
                return item.value;
            })
            .filter(Boolean);
    }

    function tempId(panel) {
        const input =
            panel.querySelector("#cons-temp-id") ||
            document.getElementById("cons-temp-id") ||
            panel.querySelector("[name='temp_id']") ||
            panel.querySelector("[name='tempId']");

        return input && input.value ? input.value.trim() : "";
    }

    async function postHtml(url, formData) {
        const response = await fetch(url + "?_=" + Date.now(), {
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

    function parseNumero(value) {
        const raw = String(value || "").replace(/[^\d-]/g, "");

        if (!raw || raw === "-") return null;

        const n = Number(raw);

        return Number.isFinite(n) ? n : null;
    }

    function formatNumber(value) {
        const n = Number(value || 0);

        return n.toLocaleString("es-BO");
    }

    function extractStatsFromResult(root) {
        const stats = {};
        const rows = Array.from(root.querySelectorAll("tr"));

        rows.forEach(function (row) {
            const cells = Array.from(row.querySelectorAll("td, th"))
                .map(function (cell) {
                    return cell.textContent.trim();
                })
                .filter(Boolean);

            if (cells.length < 2) return;

            const label = cells[0].toLowerCase();
            const value = parseNumero(cells[cells.length - 1]);

            if (value === null) return;

            if (label.includes("cargados") || label.includes("total inicial")) {
                stats.totalInicial = value;
            } else if (label.includes("con fecha") && label.includes("antes")) {
                stats.conFechaAntes = value;
            } else if (label.includes("sin fecha") && label.includes("antes")) {
                stats.sinFechaAntes = value;
            } else if (label.includes("seleccionados")) {
                stats.seleccionados = value;
            } else if (label.includes("limpiados")) {
                stats.limpiados = value;
            } else if (label.includes("con fecha") && (label.includes("despues") || label.includes("después"))) {
                stats.conFechaDespues = value;
            } else if (label.includes("sin fecha") && (label.includes("despues") || label.includes("después"))) {
                stats.sinFechaDespues = value;
            } else if (label.includes("exportados")) {
                stats.exportados = value;
            }
        });

        return stats;
    }

    function polarToCartesian(cx, cy, r, angleDeg) {
        const angleRad = (angleDeg - 90) * Math.PI / 180.0;

        return {
            x: cx + (r * Math.cos(angleRad)),
            y: cy + (r * Math.sin(angleRad))
        };
    }

    function describeArc(cx, cy, r, startAngle, endAngle) {
        const start = polarToCartesian(cx, cy, r, endAngle);
        const end = polarToCartesian(cx, cy, r, startAngle);
        const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

        return [
            "M", start.x, start.y,
            "A", r, r, 0, largeArcFlag, 0, end.x, end.y,
            "L", cx, cy,
            "Z"
        ].join(" ");
    }

    function renderPieSvg(title, subtitle, items, centerLabel) {
        const total = items.reduce(function (acc, item) {
            return acc + Number(item.valor || 0);
        }, 0);

        const colors = ["#22a8f2", "#22c55e", "#f59e0b", "#a855f7", "#ef4444"];
        let current = 0;

        let slices = "";
        let labels = "";

        if (total <= 0) {
            slices = "<circle cx='100' cy='100' r='70' fill='#111827' stroke='#263752' stroke-width='2'></circle>";
            labels = "<text x='100' y='105' text-anchor='middle' class='fg-pie-empty'>0</text>";
        } else {
            items.forEach(function (item, idx) {
                const value = Number(item.valor || 0);
                const angle = value / total * 360;
                const start = current;
                const end = current + angle;
                const mid = start + angle / 2;
                const labelPos = polarToCartesian(100, 100, 48, mid);
                const color = item.color || colors[idx % colors.length];

                if (value > 0) {
                    slices += "<path d='" + describeArc(100, 100, 75, start, end) + "' fill='" + color + "'></path>";

                    labels += ""
                        + "<text x='" + labelPos.x.toFixed(1) + "' y='" + labelPos.y.toFixed(1) + "' "
                        + "text-anchor='middle' dominant-baseline='middle' class='fg-pie-value'>"
                        + formatNumber(value)
                        + "</text>";
                }

                current = end;
            });
        }

        const legend = items.map(function (item, idx) {
            const color = item.color || colors[idx % colors.length];

            return ""
                + "<div class='fg-pie-legend-item'>"
                + "<span class='fg-pie-dot' style='background:" + color + "'></span>"
                + "<span>" + item.label + "</span>"
                + "<b>" + formatNumber(item.valor || 0) + "</b>"
                + "</div>";
        }).join("");

        return ""
            + "<article class='fg-pie-card'>"
            + "<div class='fg-pie-title'>" + title + "</div>"
            + "<div class='fg-pie-subtitle'>" + subtitle + "</div>"
            + "<div class='fg-pie-figure'>"
            + "<svg viewBox='0 0 200 200' class='fg-pie-svg'>"
            + slices
            + "<circle cx='100' cy='100' r='43' fill='#0b1222'></circle>"
            + "<text x='100' y='93' text-anchor='middle' class='fg-pie-center'>" + formatNumber(total) + "</text>"
            + "<text x='100' y='113' text-anchor='middle' class='fg-pie-center-label'>" + centerLabel + "</text>"
            + labels
            + "</svg>"
            + "</div>"
            + "<div class='fg-pie-legend'>" + legend + "</div>"
            + "</article>";
    }

    async function cargarKpiSql() {
        const params = new URLSearchParams();

        params.set("fecha_proceso", fechaProcesoCompacta());
        params.set("conexion", conexionActiva());

        const response = await fetch("/api/orion-diario-v2/fase-g/kpis?" + params.toString() + "&_=" + Date.now(), {
            credentials: "same-origin"
        });

        return await response.json();
    }

    async function renderKpiPies(resultBox) {
        const stats = extractStatsFromResult(resultBox);
        const sql = await cargarKpiSql();

        if (!sql || !sql.ok) {
            const error = sql && sql.error ? sql.error : "No se pudieron cargar KPIs SQL.";
            resultBox.insertAdjacentHTML("afterbegin", htmlError(error));
            return;
        }

        const conDespues = Number(stats.conFechaDespues ?? stats.conFechaAntes ?? 0);
        const sinDespues = Number(stats.sinFechaDespues ?? stats.sinFechaAntes ?? 0);
        const exportados = Number(stats.exportados ?? stats.totalInicial ?? (conDespues + sinDespues));
        const limpiados = Number(stats.limpiados ?? 0);

        const html = ""
            + "<section class='orion-fase-g-kpi-pies'>"
            + renderPieSvg(
                "Gestión exportada",
                "Después de aplicar filtro | Limpiados: " + formatNumber(limpiados),
                [
                    { label: "Con fecha", valor: conDespues, color: "#22a8f2" },
                    { label: "Sin fecha", valor: sinDespues, color: "#22c55e" }
                ],
                "Export."
            )
            + renderPieSvg(
                "BD fecha anterior",
                sql.fecha_anterior,
                (sql.anterior || []).map(function (x, idx) {
                    const colors = ["#22a8f2", "#22c55e", "#f59e0b"];
                    return { label: x.label, valor: x.valor, color: colors[idx] };
                }),
                "Ant."
            )
            + renderPieSvg(
                "BD fecha actual",
                sql.fecha_actual,
                (sql.actual || []).map(function (x, idx) {
                    const colors = ["#22a8f2", "#22c55e", "#f59e0b"];
                    return { label: x.label, valor: x.valor, color: colors[idx] };
                }),
                "Actual"
            )
            + "</section>";

        const old = resultBox.querySelector(".orion-fase-g-kpi-pies");

        if (old) old.remove();

        resultBox.insertAdjacentHTML("afterbegin", html);
    }

    window.aplicarFiltroYExportar = async function aplicarFiltroYExportar(trigger) {
        const panel = getResultadoPanel(trigger);

        if (!panel) {
            alert("No se encontró el panel de resultado del consolidado.");
            return false;
        }

        const seleccionados = selectedDescriptions(panel);
        const temporal = tempId(panel);

        if (!temporal) {
            panel.insertAdjacentHTML(
                "beforeend",
                htmlError("No se encontró el identificador temporal de la consulta. Ejecute nuevamente la fase G.")
            );
            return false;
        }

        if (seleccionados.length === 0) {
            const continuar = confirm(
                "No seleccionó descripciones para limpiar Fecha_Compromiso. ¿Desea exportar sin aplicar filtros?"
            );

            if (!continuar) {
                return false;
            }
        }

        const formData = new FormData();

        formData.append("fecha", fechaProceso());
        formData.append("fecha_proceso", fechaProceso());
        formData.append("meses", mesesGestion());
        formData.append("conexion", conexionActiva());
        formData.append("temp_id", temporal);
        formData.append("tempId", temporal);

        seleccionados.forEach(function (valor) {
            formData.append("descripcion", valor);
            formData.append("seleccionados", valor);
        });

        let resultBox = panel.querySelector("#orion-fase-g-export-resultado");

        if (!resultBox) {
            resultBox = document.createElement("div");
            resultBox.id = "orion-fase-g-export-resultado";
            resultBox.className = "orion-fase-g-export-resultado";
            panel.appendChild(resultBox);
        }

        resultBox.innerHTML = htmlLoading("Aplicando filtro y exportando Excel...");

        const btn = trigger || panel.querySelector("button[onclick*='aplicarFiltroYExportar']");

        if (btn) {
            btn.disabled = true;
            btn.dataset.originalText = btn.textContent;
            btn.textContent = "Exportando...";
        }

        try {
            const result = await postHtml("/accion/consolidar-aplicar", formData);
            resultBox.innerHTML = result.html;

            try {
                await renderKpiPies(resultBox);
            } catch (kpiError) {
                resultBox.insertAdjacentHTML(
                    "afterbegin",
                    htmlError("No se pudieron construir los KPI visuales: " + kpiError)
                );
            }

            if (btn) {
                btn.disabled = false;
                btn.textContent = btn.dataset.originalText || "Aplicar Filtro y Exportar a Excel";
            }

            return false;
        } catch (error) {
            resultBox.innerHTML = htmlError("Error exportando Gestión ORION: " + error);

            if (btn) {
                btn.disabled = false;
                btn.textContent = btn.dataset.originalText || "Aplicar Filtro y Exportar a Excel";
            }

            return false;
        }
    };
})();
