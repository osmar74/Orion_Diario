from pathlib import Path
import re


BLUEPRINT = Path("app/controllers/gestion_consolidada_blueprint.py")
TEMPLATE = Path("app/templates/gestion_consolidada.html")
BASE = Path("app/templates/base.html")
JS = Path("app/static/js/gestion_consolidada_main_embed.js")
CSS = Path("app/static/css/deepblack.css")
AUDIT = Path("tools/audit_gestion_consolidada.py")


# ============================================================
# 1) Permitir modo embedded en /gestion-consolidada?embedded=1
# ============================================================

bp = BLUEPRINT.read_text(encoding="utf-8")

if "embedded = request.args.get" not in bp:
    bp = bp.replace(
        '''@gestion_consolidada_bp.route("/gestion-consolidada", methods=["GET"])
def vista_gestion_consolidada():
    return render_template("gestion_consolidada.html")''',
        '''@gestion_consolidada_bp.route("/gestion-consolidada", methods=["GET"])
def vista_gestion_consolidada():
    embedded = request.args.get("embedded", "0") == "1"
    return render_template("gestion_consolidada.html", embedded=embedded)''',
        1,
    )

BLUEPRINT.write_text(bp, encoding="utf-8")


# ============================================================
# 2) Marcar body embedded en plantilla del módulo
# ============================================================

tpl = TEMPLATE.read_text(encoding="utf-8")

if "gc-embedded" not in tpl:
    tpl = tpl.replace(
        '<body class="deepblack-body gc-body">',
        '<body class="deepblack-body gc-body{% if embedded %} gc-embedded{% endif %}">',
        1,
    )

TEMPLATE.write_text(tpl, encoding="utf-8")


# ============================================================
# 3) JS: reemplazar paneles temporales en pantalla principal
# ============================================================

JS.write_text(
    r'''/* ============================================================
   CONSOLIDAR GESTIÓN v1K
   Inserta el módulo real dentro de la pantalla principal.
   ============================================================ */

(function () {
    "use strict";

    const EMBED_URL = "/gestion-consolidada?embedded=1";
    const IFRAME_ID = "gc-main-embedded-frame";

    const PLACEHOLDER_TEXTS = [
        "Fases y Pasos para Consolidar Gestión",
        "Monitor de ejecución de Consolidación de gestión",
        "Módulo en preparación.",
        "Este módulo queda reservado para consolidar gestiones",
    ];

    function normalizeText(value) {
        return String(value || "").replace(/\s+/g, " ").trim();
    }

    function hasText(el, text) {
        if (!el) {
            return false;
        }

        return normalizeText(el.innerText || el.textContent || "").includes(text);
    }

    function findElementByText(text) {
        const candidates = Array.from(document.querySelectorAll("aside, section, article, div, main"));

        return candidates.find((el) => hasText(el, text)) || null;
    }

    function closestPanel(el) {
        if (!el) {
            return null;
        }

        return (
            el.closest("aside, section, article, .panel, .card, .monitor, .monitor-panel, .content-panel, .module-panel, .gc-home-launcher")
            || el
        );
    }

    function findLauncherPanel() {
        const directButton = Array.from(document.querySelectorAll("a, button"))
            .find((el) => hasText(el, "Abrir Consolidar Gestión"));

        if (directButton) {
            return closestPanel(directButton);
        }

        const launcher = findElementByText("Tercera fase del proceso");

        if (launcher) {
            return closestPanel(launcher);
        }

        return null;
    }

    function hideTemporaryPanels() {
        let hidden = [];

        PLACEHOLDER_TEXTS.forEach((text) => {
            const found = findElementByText(text);
            const panel = closestPanel(found);

            if (panel && !hidden.includes(panel)) {
                panel.classList.add("gc-main-temp-hidden");
                panel.setAttribute("aria-hidden", "true");
                hidden.push(panel);
            }
        });

        return hidden;
    }

    function expandLayoutFrom(host, hiddenPanels) {
        if (!host) {
            return;
        }

        let node = host.parentElement;
        let steps = 0;

        while (node && steps < 8) {
            const containsHost = node.contains(host);
            const containsHidden = hiddenPanels.some((panel) => node.contains(panel));

            if (containsHost && containsHidden) {
                node.classList.add("gc-main-embedded-layout");
            }

            node = node.parentElement;
            steps += 1;
        }
    }

   List.add("gc-main-embedded-layout");
            }

            node = node.parentElement;
            steps += 1;
        function renderIframe(host) {
        if (!host) {
            return false;
        }

        host.classList.add("gc-main-embed-host");

        if (host.querySelector(`#${IFRAME_ID}`)) {
            return true;
        }

        host.innerHTML = `
            <section class="gc-main-embed-shell">
                <div class="gc-main-embed-header">
                    <div>
                        <h2>📊 Consolidar Gestión</h2>
                        <p>Proceso completo A-I integrado en la pantalla principal.</p>
                    </div>
                    <a href="${EMBED_URL.replace("?embedded=1", "")}" target="_blank" rel="noopener">
                        Abrir en pestaña completa
                    </a>
                </div>

                <iframe
                    id="${IFRAME_ID}"
                    class="gc-main-embed-frame"
                    src="${EMBED_URL}"
                    title="Consolidar Gestión"
                    loading="eager"
                ></iframe>
            </section>
        `;

        return true;
    }

    function isConsolidarVisible() {
        const activeTab = Array.from(document.querySelectorAll("button, a"))
            .find((el) => hasText(el, "Consolidar Gestión") && (
                el.classList.contains("active")
                || el.classList.contains("selected")
                || el.getAttribute("aria-selected") === "true"
                || el.getAttribute("data-active") === "1"
            ));

        if (activeTab) {
            return true;
        }

        return !!findLauncherPanel();
    }

    function integrarConsolidarGestion() {
        if (document.body.classList.contains("gc-body")) {
            return;
        }

        if (!isConsolidarVisible()) {
            return;
        }

        const host = findLauncherPanel();

        if (!host) {
            return;
        }

        const hiddenPanels = hideTemporaryPanels();

        renderIframe(host);
        expandLayoutFrom(host, hiddenPanels);
    }

    function scheduleIntegration() {
        window.setTimeout(integrarConsolidarGestion, 80);
        window.setTimeout(integrarConsolidarGestion, 350);
        window.setTimeout(integrarConsolidarGestion, 900);
    }

    document.addEventListener("DOMContentLoaded", () => {
        scheduleIntegration();

        document.addEventListener("click", (event) => {
            const target = event.target.closest("button, a");

            if (target && hasText(target, "Consolidar Gestión")) {
                scheduleIntegration();
            }
        });

        const observer = new MutationObserver(() => {
            scheduleIntegration();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });
    });

    window.integrarConsolidarGestionPantallaPrincipal = integrarConsolidarGestion;
})();
''',
    encoding="utf-8",
)


# ============================================================
# 4) Cargar JS en base.html
# ============================================================

base = BASE.read_text(encoding="utf-8")

script_line = '<script src="{{ url_for(\'static\', filename=\'js/gestion_consolidada_main_embed.js\') }}"></script>'

if script_line not in base:
    if "</body>" in base:
        base = base.replace("</body>", f"    {script_line}\n</body>", 1)
    else:
        base = base.rstrip() + "\n" + script_line + "\n"

BASE.write_text(base, encoding="utf-8")


# ============================================================
# 5) CSS integración
# ============================================================

css = CSS.read_text(encoding="utf-8")

bloque_css = r'''
/* ============================================================
   CONSOLIDAR GESTIÓN v1K - Integración en pantalla principal
   ============================================================ */

.gc-main-temp-hidden {
    display: none !important;
}

.gc-main-embedded-layout {
    grid-template-columns: minmax(0, 1fr) !important;
}

.gc-main-embedded-layout > .gc-main-temp-hidden {
    display: none !important;
}

.gc-main-embed-host {
    grid-column: 1 / -1 !important;
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    height: calc(100vh - 138px) !important;
    min-height: 680px !important;
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

/* Modo embebido del módulo: elimina encabezado duplicado y ajusta alto */
body.gc-body.gc-embedded .gc-hero {
    display: none !important;
}

body.gc-body.gc-embedded .gc-shell {
    padding: 8px !important;
}

body.gc-body.gc-embedded .gc-control-panel {
    margin-top: 0 !important;
}

@media (max-width: 1100px) {
    .gc-main-embed-host {
        height: auto !important;
        min-height: 720px !important;
    }

    .gc-main-embed-frame {
        min-height: 720px !important;
    }

    .gc-main-embed-header {
        align-items: flex-start;
        flex-direction: column;
    }
}
'''

if "CONSOLIDAR GESTIÓN v1K" not in css:
    css = css.rstrip() + "\n\n" + bloque_css.strip() + "\n"

CSS.write_text(css, encoding="utf-8")


# ============================================================
# 6) Auditoría
# ============================================================

audit = AUDIT.read_text(encoding="utf-8") if AUDIT.exists() else ""

if "v1K - integración pantalla principal" not in audit:
    extra = r'''
    print("\n[6] v1K - integración pantalla principal")
    base = read(APP / "templates" / "base.html")
    bp = read(APP / "controllers" / "gestion_consolidada_blueprint.py")
    tpl = read(APP / "templates" / "gestion_consolidada.html")
    css = read(APP / "static" / "css" / "deepblack.css")
    js_embed = APP / "static" / "js" / "gestion_consolidada_main_embed.js"

    if js_embed.exists():
        ok("JS embed pantalla principal existe")
    else:
        errors += fail("No existe gestion_consolidada_main_embed.js")

    if "gestion_consolidada_main_embed.js" in base:
        ok("base.html carga JS embed")
    else:
        errors += fail("base.html no carga JS embed")

    if "embedded = request.args.get" in bp:
        ok("Blueprint soporta embedded=1")
    else:
        errors += fail("Blueprint no soporta embedded=1")

    if "gc-embedded" in tpl:
        ok("Template soporta modo embebido")
    else:
        errors += fail("Template no soporta modo embebido")

    if "CONSOLIDAR GESTIÓN v1K" in css:
        ok("CSS v1K presente")
    else:
        errors += fail("Falta CSS v1K")
'''

    audit = audit.replace(
        '    print("\\n" + "=" * 100)',
        extra + '\n    print("\\n" + "=" * 100)',
        1,
    )

    AUDIT.write_text(audit, encoding="utf-8")


print("Integración v1K aplicada: Consolidar Gestión se embebe en la pantalla principal.")