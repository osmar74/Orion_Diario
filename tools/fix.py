from pathlib import Path


JS = Path("app/static/js/gestion_consolidada_main_embed.js")
CSS = Path("app/static/css/deepblack.css")
AUDIT = Path("tools/audit_gestion_consolidada.py")


JS.write_text(
    r'''/* ============================================================
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
''',
    encoding="utf-8",
)


css = CSS.read_text(encoding="utf-8")

bloque_css = r'''
/* ============================================================
   CONSOLIDAR GESTIÓN v1K.2 - Layout embed corregido
   ============================================================ */

.gc-main-temp-hidden {
    display: none !important;
}

.gc-main-consolidar-common {
    grid-template-columns: minmax(0, 1fr) !important;
}

.gc-main-consolidar-monitor-column {
    grid-column: 1 / -1 !important;
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
}

.gc-main-embed-host {
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    height: calc(100vh - 142px) !important;
    min-height: 720px !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: hidden !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}

.gc-main-embed-shell {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background: rgba(15, 23, 42, 0.72);
    border: 1px solid rgba(96, 165, 250, 0.28);
    border-radius: 18px;
    overflow: hidden;
}

.gc-main-embed-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex: 0 0 auto;
    padding: 10px 14px;
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 64, 175, 0.28));
    border-bottom: 1px solid rgba(96, 165, 250, 0.22);
}

.gc-main-embed-header h2 {
    margin: 0;
    color: #e5e7eb;
    font-size: 1rem;
}

.gc-main-embed-header p {
    margin: 2px 0 0 0;
    color: #94a3b8;
    font-size: 0.74rem;
}

.gc-main-embed-header a {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 30px;
    padding: 6px 11px;
    border-radius: 999px;
    color: #dbeafe;
    text-decoration: none;
    font-weight: 900;
    font-size: 0.74rem;
    white-space: nowrap;
    background: rgba(37, 99, 235, 0.22);
    border: 1px solid rgba(96, 165, 250, 0.34);
}

.gc-main-embed-frame {
    flex: 1 1 auto;
    width: 100%;
    height: 100%;
    min-height: 0;
    border: 0;
    background: #05070a;
}

/* Modo embebido: quitar encabezado duplicado */
body.gc-body.gc-embedded .gc-hero {
    display: none !important;
}

body.gc-body.gc-embedded .gc-shell {
    padding: 8px !important;
}

/* Forzar Estado de fases lateral dentro del iframe, aunque el iframe sea angosto */
body.gc-body.gc-embedded .gc-work-layout {
    display: grid !important;
    grid-template-columns: 215px minmax(0, 1fr) !important;
    gap: 10px !important;
    overflow: hidden !important;
}

body.gc-body.gc-embedded .gc-phase-sidebar {
    display: block !important;
    position: static !important;
    height: 100% !important;
    min-height: 0 !important;
    overflow: hidden !important;
}

body.gc-body.gc-embedded .gc-phase-sidebar .gc-state-section {
    height: 100% !important;
    max-height: none !important;
    overflow-y: auto !important;
}

body.gc-body.gc-embedded .gc-process-panels {
    min-width: 0 !important;
    height: 100% !important;
    overflow-y: auto !important;
}

/* Anular el responsive previo solo para el iframe embebido */
@media (max-width: 1180px) {
    body.gc-body.gc-embedded .gc-work-layout {
        grid-template-columns: 215px minmax(0, 1fr) !important;
        overflow: hidden !important;
    }

    body.gc-body.gc-embedded .gc-phase-sidebar,
    body.gc-body.gc-embedded .gc-phase-sidebar .gc-state-section,
    body.gc-body.gc-embedded .gc-process-panels {
        height: 100% !important;
        max-height: none !important;
    }
}

@media (max-width: 900px) {
    body.gc-body.gc-embedded .gc-work-layout {
        grid-template-columns: 1fr !important;
        overflow: visible !important;
    }

    body.gc-body.gc-embedded .gc-phase-sidebar,
    body.gc-body.gc-embedded .gc-phase-sidebar .gc-state-section,
    body.gc-body.gc-embedded .gc-process-panels {
        height: auto !important;
        overflow: visible !important;
    }

    .gc-main-embed-host {
        height: auto !important;
        min-height: 760px !important;
    }

    .gc-main-embed-frame {
        min-height: 760px !important;
    }
}
'''

if "CONSOLIDAR GESTIÓN v1K.2" not in css:
    css = css.rstrip() + "\n\n" + bloque_css.strip() + "\n"

CSS.write_text(css, encoding="utf-8")


audit = AUDIT.read_text(encoding="utf-8")

if "CONSOLIDAR GESTIÓN v1K.2" not in audit:
    audit = audit.replace(
        '''        "CONSOLIDAR GESTIÓN v1K.1",''',
        '''        "CONSOLIDAR GESTIÓN v1K.1",
        "CONSOLIDAR GESTIÓN v1K.2",''',
        1,
    )

AUDIT.write_text(audit, encoding="utf-8")

print("Fix v1K.2 aplicado: oculta panel temporal izquierdo y fuerza Estado de fases lateral en embed.")