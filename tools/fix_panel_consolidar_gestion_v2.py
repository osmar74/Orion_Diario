from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

STATIC_JS_DIR = ROOT / "app" / "static" / "js"
FIX_JS = STATIC_JS_DIR / "orion_panel_router_fix.js"

TEMPLATES_DIR = ROOT / "app" / "templates"

BACKUP_ROOT = ROOT / ".git" / "orion_patch_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")

SCRIPT_TAG = "{{ url_for('static', filename='js/orion_panel_router_fix.js') }}"
SCRIPT_HTML = f'<script src="{SCRIPT_TAG}"></script>'

JS_CONTENT = r"""
(function () {
    "use strict";

    /*
      Orion Panel Router Fix v2

      Diagnóstico:
      - OrionPanelFix.findPanel("consolidar") devolvía null.
      - Eso significa que el panel Consolidar Gestión no estaba oculto,
        sino que ya no existía en el DOM después de navegar varias veces.

      Solución:
      - No intenta mostrar un panel inexistente.
      - Si al hacer clic en Consolidar Gestión el contenido queda vacío,
        ejecuta automáticamente:
            Inicio -> Consolidar Gestión
      - Esto reproduce la acción manual que ya comprobaste que funciona.
    */

    var VERSION = "v2.0.0";
    var DEBUG = false;
    var repairing = false;
    var lastAction = null;
    var lastRepairAt = 0;
    var repairCount = 0;
    var MAX_REPAIRS = 3;

    function log() {
        if (!DEBUG) return;
        console.log.apply(console, ["[OrionPanelFix " + VERSION + "]"].concat(Array.from(arguments)));
    }

    function normalizeText(value) {
        return String(value || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/\s+/g, " ")
            .trim();
    }

    function textOf(el) {
        if (!el) return "";
        return normalizeText(
            el.innerText ||
            el.textContent ||
            el.value ||
            el.getAttribute("aria-label") ||
            ""
        );
    }

    function metaOf(el) {
        if (!el) return "";

        var attrs = [
            "id",
            "class",
            "name",
            "href",
            "data-panel",
            "data-target",
            "data-section",
            "data-view",
            "data-url",
            "data-route",
            "aria-controls",
            "aria-label"
        ];

        var values = [];

        attrs.forEach(function (attr) {
            values.push(el.getAttribute(attr));
        });

        try {
            Object.keys(el.dataset || {}).forEach(function (k) {
                values.push(k);
                values.push(el.dataset[k]);
            });
        } catch (e) {}

        values.push(textOf(el));

        return normalizeText(values.join(" "));
    }

    function detectActionFromText(value) {
        var t = normalizeText(value);

        if (!t) return null;

        if (t === "inicio" || t.includes(" inicio ")) {
            return "inicio";
        }

        if (t.includes("gestion diaria orion")) {
            return "orion";
        }

        if (t.includes("gestion diaria aster")) {
            return "aster";
        }

        if (
            t.includes("consolidar gestion") ||
            t.includes("gestion consolidada") ||
            t.includes("consolidacion")
        ) {
            return "consolidar";
        }

        if (t === "logs" || t.includes(" logs ")) {
            return "logs";
        }

        return null;
    }

    function detectActionFromElement(el) {
        var current = el;

        while (current && current !== document.body && current !== document.documentElement) {
            var actionByText = detectActionFromText(textOf(current));
            if (actionByText) return actionByText;

            var actionByMeta = detectActionFromText(metaOf(current));
            if (actionByMeta) return actionByMeta;

            current = current.parentElement;
        }

        return null;
    }

    function isNavElement(el) {
        if (!el) return false;

        return !!(
            el.closest("nav") ||
            el.closest("header") ||
            el.closest(".navbar") ||
            el.closest(".sidebar") ||
            el.closest(".menu") ||
            el.closest(".nav") ||
            el.closest(".tabs")
        );
    }

    function getButtons() {
        return Array.from(document.querySelectorAll("button, a, [role='button'], input[type='button'], input[type='submit']"));
    }

    function findButton(action) {
        var buttons = getButtons();

        for (var i = 0; i < buttons.length; i++) {
            if (detectActionFromElement(buttons[i]) === action) {
                return buttons[i];
            }
        }

        return null;
    }

    function clickButton(action) {
        var btn = findButton(action);

        if (!btn) {
            log("No se encontró botón", action);
            return false;
        }

        log("Click programático", action, btn);

        btn.dispatchEvent(new MouseEvent("click", {
            bubbles: true,
            cancelable: true,
            view: window
        }));

        return true;
    }

    function getNonNavText() {
        var clone = document.body.cloneNode(true);

        Array.from(clone.querySelectorAll("nav, header, .navbar, .sidebar, .menu, .nav, .tabs, script, style"))
            .forEach(function (el) {
                el.remove();
            });

        return normalizeText(clone.innerText || clone.textContent || "");
    }

    function pageHasMeaningfulContent() {
        var t = getNonNavText();

        var removable = [
            "orion procesos",
            "gestion diaria orion",
            "gestion diaria aster",
            "consolidar gestion",
            "inicio",
            "logs",
            "reset"
        ];

        removable.forEach(function (x) {
            t = t.replaceAll(normalizeText(x), "");
        });

        t = normalizeText(t);

        return t.length > 20;
    }

    function pageLooksEmpty() {
        return !pageHasMeaningfulContent();
    }

    function pageLooksLikeConsolidar() {
        var t = getNonNavText();

        return (
            t.includes("consolidar") ||
            t.includes("consolidacion") ||
            t.includes("gestion consolidada") ||
            t.includes("fase") ||
            t.includes("consolidado")
        );
    }

    function isProbablyPanel(el) {
        if (!el || !el.tagName) return false;
        if (isNavElement(el)) return false;

        var meta = metaOf(el);

        return (
            el.matches("main, section, article") ||
            el.getAttribute("role") === "tabpanel" ||
            el.hasAttribute("data-panel") ||
            el.hasAttribute("data-section") ||
            el.hasAttribute("data-view") ||
            meta.includes("panel") ||
            meta.includes("content") ||
            meta.includes("contenido") ||
            meta.includes("vista") ||
            meta.includes("seccion") ||
            meta.includes("section") ||
            meta.includes("consolidar") ||
            meta.includes("consolidacion") ||
            meta.includes("gestion consolidada")
        );
    }

    function getPanelCandidates() {
        var selectors = [
            "main",
            "section",
            "article",
            "[role='tabpanel']",
            "[data-panel]",
            "[data-section]",
            "[data-view]",
            ".panel",
            ".tab-pane",
            ".page",
            ".view",
            ".content",
            ".content-panel",
            ".section-panel",
            "div[id*='panel']",
            "div[class*='panel']",
            "div[id*='contenido']",
            "div[class*='contenido']",
            "div[id*='content']",
            "div[class*='content']",
            "div[id*='consolidar']",
            "div[class*='consolidar']",
            "div[id*='consolidacion']",
            "div[class*='consolidacion']"
        ];

        var found = [];

        selectors.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (el) {
                if (found.indexOf(el) === -1 && isProbablyPanel(el)) {
                    found.push(el);
                }
            });
        });

        return found;
    }

    function findPanel(action) {
        var candidates = getPanelCandidates();
        var best = null;
        var bestScore = 0;

        candidates.forEach(function (el) {
            var meta = metaOf(el);
            var score = 0;

            if (action === "consolidar") {
                if (meta.includes("consolidar")) score += 100;
                if (meta.includes("consolidacion")) score += 80;
                if (meta.includes("gestion consolidada")) score += 80;
            }

            if (action === "inicio" && meta.includes("inicio")) score += 100;
            if (action === "orion" && meta.includes("orion")) score += 100;
            if (action === "aster" && meta.includes("aster")) score += 100;

            if (score > bestScore) {
                best = el;
                bestScore = score;
            }
        });

        return bestScore > 0 ? best : null;
    }

    function repairConsolidarIfNeeded(reason) {
        var now = Date.now();

        if (repairing) {
            return {
                ok: false,
                status: "already_repairing",
                version: VERSION
            };
        }

        if (pageLooksLikeConsolidar() && !pageLooksEmpty()) {
            return {
                ok: true,
                status: "already_visible",
                version: VERSION
            };
        }

        if (!pageLooksEmpty() && lastAction !== "consolidar") {
            return {
                ok: true,
                status: "page_not_empty",
                version: VERSION
            };
        }

        if (now - lastRepairAt < 600) {
            return {
                ok: false,
                status: "too_soon",
                version: VERSION
            };
        }

        if (repairCount >= MAX_REPAIRS) {
            console.warn("[OrionPanelFix] Límite de reparaciones alcanzado. Revisa el router original.");
            return {
                ok: false,
                status: "max_repairs_reached",
                version: VERSION
            };
        }

        var inicioBtn = findButton("inicio");
        var consolidarBtn = findButton("consolidar");

        if (!inicioBtn || !consolidarBtn) {
            console.warn("[OrionPanelFix] No se encontraron botones necesarios.", {
                inicio: !!inicioBtn,
                consolidar: !!consolidarBtn
            });

            return {
                ok: false,
                status: "missing_buttons",
                inicio: !!inicioBtn,
                consolidar: !!consolidarBtn,
                version: VERSION
            };
        }

        repairing = true;
        lastRepairAt = now;
        repairCount += 1;

        console.warn("[OrionPanelFix] Restaurando Consolidar Gestión con secuencia Inicio -> Consolidar.", {
            reason: reason || "manual_or_empty_panel",
            repairCount: repairCount
        });

        clickButton("inicio");

        window.setTimeout(function () {
            clickButton("consolidar");
        }, 250);

        window.setTimeout(function () {
            repairing = false;

            if (pageLooksEmpty()) {
                console.warn("[OrionPanelFix] El panel sigue vacío después del intento de reparación.");
            }
        }, 900);

        return {
            ok: true,
            status: "repair_started",
            version: VERSION,
            repairCount: repairCount
        };
    }

    function scheduleCheck(action) {
        window.setTimeout(function () {
            if (action !== "consolidar") return;

            if (pageLooksEmpty() || !pageLooksLikeConsolidar()) {
                repairConsolidarIfNeeded("after_consolidar_click");
            }
        }, 350);

        window.setTimeout(function () {
            if (action !== "consolidar") return;

            if (pageLooksEmpty() || !pageLooksLikeConsolidar()) {
                repairConsolidarIfNeeded("late_check_after_consolidar_click");
            }
        }, 1000);
    }

    document.addEventListener("click", function (event) {
        var trigger = event.target.closest("button, a, [role='button'], input[type='button'], input[type='submit']");

        if (!trigger) return;

        var action = detectActionFromElement(trigger);

        if (!action) return;

        lastAction = action;

        if (action !== "consolidar") {
            repairCount = 0;
        }

        log("click detectado", action);

        scheduleCheck(action);
    }, true);

    window.OrionPanelFix = {
        version: VERSION,
        findPanel: findPanel,
        repairConsolidarIfNeeded: repairConsolidarIfNeeded,
        clickButton: clickButton,
        findButton: findButton,
        pageLooksEmpty: pageLooksEmpty,
        pageLooksLikeConsolidar: pageLooksLikeConsolidar,
        getNonNavText: getNonNavText,
        debug: function () {
            return {
                version: VERSION,
                lastAction: lastAction,
                repairing: repairing,
                repairCount: repairCount,
                pageLooksEmpty: pageLooksEmpty(),
                pageLooksLikeConsolidar: pageLooksLikeConsolidar(),
                nonNavText: getNonNavText(),
                buttons: getButtons().map(function (b) {
                    return {
                        text: textOf(b),
                        meta: metaOf(b),
                        action: detectActionFromElement(b)
                    };
                }),
                panelConsolidar: findPanel("consolidar")
            };
        },
        setDebug: function (value) {
            DEBUG = !!value;
            return {
                debug: DEBUG,
                version: VERSION
            };
        }
    };

    console.info("[OrionPanelFix] cargado", VERSION);
})();
""".strip() + "\n"


def title(value):
    print("\n" + "=" * 90)
    print(value)
    print("=" * 90)


def read(path):
    return path.read_text(encoding="utf-8", errors="ignore")


def write(path, content):
    path.write_text(content, encoding="utf-8")


def backup(path):
    if not path.exists():
        return

    rel = path.relative_to(ROOT)
    dest = BACKUP_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    print(f"Backup: {rel} -> {dest}")


def find_templates():
    if not TEMPLATES_DIR.exists():
        raise FileNotFoundError(f"No existe: {TEMPLATES_DIR}")

    candidates = []

    for path in TEMPLATES_DIR.rglob("*.html"):
        text = read(path)
        lower = text.lower()

        score = 0

        for kw in [
            "orion procesos",
            "gestión diaria orion",
            "gestion diaria orion",
            "gestión diaria aster",
            "gestion diaria aster",
            "consolidar gestión",
            "consolidar gestion",
            "logs",
            "reset",
        ]:
            if kw in lower:
                score += 10

        if "</body>" in lower:
            score += 1

        if score > 0:
            candidates.append((score, path))

    candidates.sort(reverse=True, key=lambda x: x[0])
    return [path for _, path in candidates]


def inject_script(path):
    text = read(path)

    if "orion_panel_router_fix.js" in text:
        print(f"OK: ya estaba inyectado en {path.relative_to(ROOT)}")
        return

    backup(path)

    lower = text.lower()

    if "</body>" in lower:
        idx = lower.rfind("</body>")
        new_text = text[:idx].rstrip() + "\n    " + SCRIPT_HTML + "\n" + text[idx:]
    else:
        new_text = text.rstrip() + "\n" + SCRIPT_HTML + "\n"

    write(path, new_text)
    print(f"OK: script inyectado en {path.relative_to(ROOT)}")


def main():
    title("FIX V2 - PANEL CONSOLIDAR GESTION")

    print(f"Root: {ROOT}")
    print(f"Archivo JS: {FIX_JS}")

    title("1. CREANDO / REEMPLAZANDO JS")
    STATIC_JS_DIR.mkdir(parents=True, exist_ok=True)
    backup(FIX_JS)
    write(FIX_JS, JS_CONTENT)
    print(f"OK: actualizado {FIX_JS.relative_to(ROOT)}")

    title("2. BUSCANDO TEMPLATE PRINCIPAL")
    templates = find_templates()

    if not templates:
        raise RuntimeError("No encontré template con navegación Orion. Pega el resultado de tree app\\templates.")

    print("Templates candidatos:")
    for p in templates:
        print(f"- {p.relative_to(ROOT)}")

    selected = templates[0]
    print(f"\nTemplate seleccionado: {selected.relative_to(ROOT)}")

    inject_script(selected)

    title("3. VALIDACION")
    subprocess.run([sys.executable, "-m", "py_compile", str(Path(__file__))], check=True)
    print("OK: script Python válido.")

    title("FINALIZADO")
    print("Ahora ejecuta:")
    print("  python run.py")
    print("")
    print("En navegador:")
    print("  Ctrl + F5")
    print("")
    print("En consola F12 valida:")
    print("  OrionPanelFix.version")
    print("  OrionPanelFix.debug()")
    print("  OrionPanelFix.repairConsolidarIfNeeded()")


if __name__ == "__main__":
    main()