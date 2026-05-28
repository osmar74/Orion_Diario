/* ============================================================
   CONSOLIDAR GESTIÓN v1K.2
   Embed real en pantalla principal:
   - Oculta paneles temporales.
   - Expande monitor a todo el ancho.
   - Mantiene Estado de fases lateral dentro del iframe.
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
        return String((el && (el.innerText || el.textContent)) || "").replace(/\s+/g, " ").trim();
    }

    function hasText(el, text) {
        return textOf(el).includes(text);
    }

    function findByText(text) {
        var nodes = Array.from(document.querySelectorAll("aside, section, article, div, main"));

        return nodes.find(function (el) {
            return hasText(el, text);
        }) || null;
    }

    function findLauncherPanel() {
        var btn = Array.from(document.querySelectorAll("a, button")).find(function (el) {
            return hasText(el, "Abrir Consolidar Gestión");
        });

        if (btn) {
            return btn.closest("section, article, aside, .gc-home-launcher, .panel, .card, div") || btn;
        }

        var textPanel = findByText("Tercera fase del proceso");

        if (textPanel) {
            return textPanel.closest("section, article, aside, .gc-home-launcher, .panel, .card, div") || textPanel;
        }

        return null;
    }

    function ancestors(el) {
        var list = [];

        while (el) {
            list.push(el);
            el = el.parentElement;
        }

        return list;
    }

    function commonAncestor(a, b) {
        if (!a || !b) {
            return null;
        }

        var aa = ancestors(a);
        var bb = ancestors(b);

        return aa.find(function (node) {
            return bb.includes(node);
        }) || null;
    }

    function childUnder(parent, el) {
        if (!parent || !el) {
            return null;
        }

        var current = el;

        while (current && current.parentElement !== parent) {
            current = current.parentElement;
        }

        return current;
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
            el.classList.remove("gc-main-temp-hidden");
            el.removeAttribute("aria-hidden");
        });

        hiddenElements = [];

        document.querySelectorAll(".gc-main-consolidar-common").forEach(function (el) {
            el.classList.remove("gc-main-consolidar-common");
        });

        document.querySelectorAll(".gc-main-consolidar-monitor-column").forEach(function (el) {
            el.classList.remove("gc-main-consolidar-monitor-column");
        });
    }

    function setTituloConsolidar() {
        var titulo =
            document.querySelector(".monitor-header h2") ||
            document.querySelector(".monitor h2") ||
            document.querySelector("main h2");

        if (titulo) {
            titulo.textContent = "📊 Monitor de ejecución de Consolidar Gestión";
        }
    }

    function crearHtmlEmbed() {
        var html = "";

        html += "<section class=\"gc-main-embed-shell\">";
        html += "  <div class=\"gc-main-embed-header\">";
        html += "    <div>";
        html += "      <h2>📊 Consolidar Gestión</h2>";
        html += "      <p>Proceso completo A-I integrado en la pantalla principal.</p>";
        html += "    </div>";
        html += "    <a href=\"/gestion-consolidada\" target=\"_blank\" rel=\"noopener\">";
        html += "      Abrir en pestaña completa";
        html += "    </a>";
        html += "  </div>";
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

    function ocultarTemporalesYExpandir(host) {
        var launcher = findLauncherPanel();
        var sidebarTemp = findByText("Fases y Pasos para Consolidar Gestión");
        var monitorTemp = findByText("Módulo en preparación.") || findByText("Este módulo queda reservado para consolidar gestiones");

        var referencias = [launcher, sidebarTemp, monitorTemp].filter(Boolean);

        referencias.forEach(function (ref) {
            var common = commonAncestor(host, ref);

            if (!common) {
                return;
            }

            var hostChild = childUnder(common, host);
            var refChild = childUnder(common, ref);

            if (common && hostChild && refChild && hostChild !== refChild) {
                common.classList.add("gc-main-consolidar-common");
                hostChild.classList.add("gc-main-consolidar-monitor-column");
                hideElement(refChild);
            }
        });

        // Fallback para el panel azul temporal cuando queda como hermano directo visible.
        var launcherFallback = findLauncherPanel();

        if (launcherFallback && !launcherFallback.contains(host)) {
            var panel = launcherFallback.closest("section, article, aside, .panel, .card, .gc-home-launcher, div") || launcherFallback;
            hideElement(panel);
        }
    }

    function integrarConsolidarGestion() {
        var host = byId("monitor-content");

        if (!host) {
            return false;
        }

        setTituloConsolidar();
        ocultarTemporalesYExpandir(host);

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

        if (window.__gcSeleccionarModuloWrappedV1K2) {
            return;
        }

        originalSeleccionarModulo = window.seleccionarModulo;

        window.seleccionarModulo = function (modulo) {
            var resultado = originalSeleccionarModulo.apply(this, arguments);

            window.setTimeout(function () {
                if (String(modulo || "").toLowerCase() === "consolidar") {
                    integrarConsolidarGestion();
                } else {
                    restoreHiddenElements();
                }
            }, 120);

            return resultado;
        };

        window.__gcSeleccionarModuloWrappedV1K2 = true;
    }

    function inicializar() {
        envolverSeleccionarModulo();

        var btn = byId("btnModuloConsolidar");

        if (btn) {
            btn.addEventListener("click", function () {
                window.setTimeout(integrarConsolidarGestion, 120);
                window.setTimeout(integrarConsolidarGestion, 500);
            });
        }

        window.setTimeout(function () {
            if (btn && (btn.classList.contains("active") || btn.classList.contains("selected"))) {
                integrarConsolidarGestion();
            }
        }, 300);
    }

    document.addEventListener("DOMContentLoaded", inicializar);

    window.integrarConsolidarGestionPantallaPrincipal = integrarConsolidarGestion;
})();
