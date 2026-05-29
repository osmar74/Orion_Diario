/* ============================================================
   CONSOLIDAR GESTIÓN v1K.3
   Limpieza final de integración:
   - Quita launcher temporal.
   - Oculta panel izquierdo temporal.
   - Usa el monitor principal como contenedor limpio.
   - No afecta ORION ni ASTER.
   ============================================================ */

(function () {
    "use strict";

    var EMBED_URL = "/gestion-consolidada?embedded=1";
    var FRAME_ID = "gc-main-embedded-frame";
    var originalSeleccionarModulo = null;
    var hiddenElements = [];

    function byId(id) {
        return document.getElementById(id);
    }

    function textOf(el) {
        return String((el && (el.innerText || el.textContent)) || "")
            .replace(/\s+/g, " ")
            .trim();
    }

    function hasText(el, text) {
        return textOf(el).includes(text);
    }

    function allCandidates() {
        return Array.from(document.querySelectorAll(
            "aside, section, article, main, div, .panel, .card, .module-panel, .content-panel, .gc-home-launcher"
        ));
    }

    function findPanelsByText(text) {
        var found = [];

        allCandidates().forEach(function (el) {
            if (!hasText(el, text)) {
                return;
            }

            var rect = el.getBoundingClientRect();
            var area = Math.max(0, rect.width) * Math.max(0, rect.height);

            found.push({
                el: el,
                area: area,
                width: rect.width,
                height: rect.height
            });
        });

        found.sort(function (a, b) {
            return a.area - b.area;
        });

        return found.map(function (item) {
            return item.el;
        });
    }

    function findBestPanelByText(text) {
        var panels = findPanelsByText(text);

        if (!panels.length) {
            return null;
        }

        // Preferir paneles grandes pero no body/html.
        var large = panels.filter(function (el) {
            var rect = el.getBoundingClientRect();
            return (
                el !== document.body &&
                el !== document.documentElement &&
                rect.width >= 180 &&
                rect.height >= 80
            );
        });

        if (large.length) {
            return large[0];
        }

        return panels[0];
    }

    function findLauncherPanel() {
        var launcher = document.querySelector(".gc-home-launcher, [data-gc-home-launcher='1']");

        if (launcher) {
            return launcher;
        }

        var byText = findBestPanelByText("Tercera fase del proceso");

        if (byText) {
            return byText;
        }

        var btn = Array.from(document.querySelectorAll("a, button")).find(function (el) {
            return hasText(el, "Abrir Consolidar Gestión");
        });

        if (!btn) {
            return null;
        }

        var parent = btn;

        for (var i = 0; i < 8 && parent; i += 1) {
            var rect = parent.getBoundingClientRect();

            if (
                parent !== document.body &&
                parent !== document.documentElement &&
                rect.width >= 300 &&
                rect.height >= 100
            ) {
                return parent;
            }

            parent = parent.parentElement;
        }

        return btn;
    }

    function hideElement(el) {
        if (!el || el === document.body || el === document.documentElement) {
            return;
        }

        if (!hiddenElements.includes(el)) {
            hiddenElements.push(el);
        }

        el.classList.add("gc-main-temp-hidden");
        el.setAttribute("aria-hidden", "true");
    }

    function restoreHiddenElements() {
        hiddenElements.forEach(function (el) {
            if (!el) {
                return;
            }

            el.classList.remove("gc-main-temp-hidden");
            el.removeAttribute("aria-hidden");
        });

        hiddenElements = [];

        document.body.classList.remove("gc-consolidar-active");

        document.querySelectorAll(".gc-main-monitor-clean").forEach(function (el) {
            el.classList.remove("gc-main-monitor-clean");
        });

        document.querySelectorAll(".gc-main-layout-clean").forEach(function (el) {
            el.classList.remove("gc-main-layout-clean");
        });
    }

    function findMonitorHost() {
        return (
            byId("monitor-content") ||
            document.querySelector("[data-monitor-content]") ||
            document.querySelector(".monitor-content")
        );
    }

    function findMonitorContainer(host) {
        if (!host) {
            return null;
        }

        var parent = host.parentElement;

        for (var i = 0; i < 8 && parent; i += 1) {
            var texto = textOf(parent);

            if (
                texto.includes("Monitor de ejecución") ||
                parent.classList.contains("monitor") ||
                parent.classList.contains("monitor-panel") ||
                parent.classList.contains("panel-monitor")
            ) {
                return parent;
            }

            parent = parent.parentElement;
        }

        return host.parentElement;
    }

    function findMainLayout(host) {
        if (!host) {
            return null;
        }

        var parent = host.parentElement;

        for (var i = 0; i < 10 && parent; i += 1) {
            var rect = parent.getBoundingClientRect();

            if (
                parent !== document.body &&
                parent !== document.documentElement &&
                rect.width > 800 &&
                rect.height > 400
            ) {
                return parent;
            }

            parent = parent.parentElement;
        }

        return null;
    }

    function crearHtmlEmbed() {
        var html = "";

        html += "<section class=\"gc-main-embed-shell\">";
        html += "  <iframe";
        html += "    id=\"" + FRAME_ID + "\"";
        html += "    class=\"gc-main-embed-frame\"";
        html += "    src=\"" + EMBED_URL + "\"";
        html += "    title=\"Consolidar Gestión\"";
        html += "    loading=\"eager\">";
        html += "  </iframe>";
        html += "</section>";

        return html;
    }

    function ocultarPanelesTemporales() {
        var sidebarTemp = findBestPanelByText("Fases y Pasos para Consolidar Gestión");
        var launcher = findLauncherPanel();

        hideElement(sidebarTemp);
        hideElement(launcher);

        // Ocultar cualquier launcher residual que esté suelto.
        document.querySelectorAll(".gc-home-launcher, [data-gc-home-launcher='1']").forEach(function (el) {
            hideElement(el);
        });
    }

    function integrarConsolidarGestion() {
        var host = findMonitorHost();

        if (!host) {
            return false;
        }

        document.body.classList.add("gc-consolidar-active");

        ocultarPanelesTemporales();

        var monitorContainer = findMonitorContainer(host);

        if (monitorContainer) {
            monitorContainer.classList.add("gc-main-monitor-clean");
        }

        var mainLayout = findMainLayout(host);

        if (mainLayout) {
            mainLayout.classList.add("gc-main-layout-clean");
        }

        host.classList.add("gc-main-embed-host");

        if (!host.querySelector("#" + FRAME_ID)) {
            host.innerHTML = crearHtmlEmbed();
        }

        return true;
    }

    function envolverSeleccionarModulo() {
        if (typeof window.seleccionarModulo !== "function") {
            return;
        }

        if (window.__gcSeleccionarModuloWrappedV1K3) {
            return;
        }

        originalSeleccionarModulo = window.seleccionarModulo;

        window.seleccionarModulo = function (modulo) {
            var resultado = originalSeleccionarModulo.apply(this, arguments);
            var nombre = String(modulo || "").toLowerCase();

            window.setTimeout(function () {
                if (nombre === "consolidar") {
                    integrarConsolidarGestion();
                    window.setTimeout(integrarConsolidarGestion, 350);
                } else {
                    restoreHiddenElements();
                }
            }, 100);

            return resultado;
        };

        window.__gcSeleccionarModuloWrappedV1K3 = true;
    }

    function bindBotonConsolidar() {
        var botones = Array.from(document.querySelectorAll("button, a"));

        botones.forEach(function (btn) {
            if (!hasText(btn, "Consolidar Gestión")) {
                return;
            }

            if (btn.__gcBindConsolidar) {
                return;
            }

            btn.__gcBindConsolidar = true;

            btn.addEventListener("click", function () {
                window.setTimeout(integrarConsolidarGestion, 120);
                window.setTimeout(integrarConsolidarGestion, 450);
            });
        });
    }

    function inicializar() {
        envolverSeleccionarModulo();
        bindBotonConsolidar();

        window.setTimeout(bindBotonConsolidar, 500);

        // Si la pestaña Consolidar quedó activa al recargar.
        window.setTimeout(function () {
            var active = Array.from(document.querySelectorAll("button, a")).find(function (el) {
                return (
                    hasText(el, "Consolidar Gestión") &&
                    (
                        el.classList.contains("active") ||
                        el.classList.contains("selected") ||
                        el.getAttribute("aria-selected") === "true"
                    )
                );
            });

            if (active) {
                integrarConsolidarGestion();
            }
        }, 300);
    }

    document.addEventListener("DOMContentLoaded", inicializar);

    window.integrarConsolidarGestionPantallaPrincipal = integrarConsolidarGestion;
})();
