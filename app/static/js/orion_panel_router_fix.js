(function () {
    "use strict";

    /*
      Orion Panel Router Fix v3

      Problema corregido:
      - v2 daba falso positivo porque leía textos del header/navbar:
        "Consolidar Gestión", "Inicio", "Logs", "Reset".
      - La pantalla podía estar vacía, pero el fix respondía already_visible.

      Estrategia v3:
      - Detecta contenido real debajo del header.
      - Si se presiona "Consolidar Gestión" y el área real queda vacía,
        ejecuta automáticamente:
            Inicio -> Consolidar Gestión
      - No considera el header/navbar como contenido válido.
    */

    var VERSION = "v3.0.0";
    var DEBUG = false;

    var repairing = false;
    var lastAction = null;
    var repairCount = 0;
    var lastRepairAt = 0;
    var MAX_REPAIRS = 5;

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
            "onclick",
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

        if (t === "inicio") {
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

        if (t === "logs") {
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

    function getButtons() {
        return Array.from(
            document.querySelectorAll(
                "button, a, [role='button'], input[type='button'], input[type='submit']"
            )
        );
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
            console.warn("[OrionPanelFix] No se encontró botón:", action);
            return false;
        }

        log("Click programático:", action, btn);

        btn.dispatchEvent(new MouseEvent("click", {
            bubbles: true,
            cancelable: true,
            view: window
        }));

        return true;
    }

    function getHeaderBottom() {
        var candidates = Array.from(document.querySelectorAll(
            "header, nav, .navbar, .topbar, .app-header, .main-header, .orion-header, .sidebar, .menu, .nav"
        ));

        var maxBottom = 0;

        candidates.forEach(function (el) {
            var rect = el.getBoundingClientRect();

            if (rect.width <= 0 || rect.height <= 0) return;

            if (rect.top < 260) {
                maxBottom = Math.max(maxBottom, rect.bottom);
            }
        });

        /*
          Fallback para tu layout:
          El header visual ocupa aprox. hasta y=200.
          Si no se detecta por clases, usamos 205.
        */
        if (maxBottom < 120) {
            maxBottom = 205;
        }

        return maxBottom;
    }

    function isVisible(el) {
        if (!el) return false;

        var style = window.getComputedStyle(el);

        if (style.display === "none") return false;
        if (style.visibility === "hidden") return false;
        if (style.opacity === "0") return false;

        var rect = el.getBoundingClientRect();

        if (rect.width <= 0 || rect.height <= 0) return false;

        return true;
    }

    function isNavigationLike(el) {
        if (!el) return false;

        return !!(
            el.closest("header") ||
            el.closest("nav") ||
            el.closest(".navbar") ||
            el.closest(".topbar") ||
            el.closest(".app-header") ||
            el.closest(".main-header") ||
            el.closest(".orion-header") ||
            el.closest(".sidebar") ||
            el.closest(".menu") ||
            el.closest(".nav")
        );
    }

    function getRealContentElements() {
        var headerBottom = getHeaderBottom();

        var selectors = [
            "main",
            "section",
            "article",
            ".container",
            ".container-fluid",
            ".content",
            ".main-content",
            ".page-content",
            ".panel",
            ".card",
            ".row",
            ".col",
            ".col-md-12",
            ".col-lg-12",
            "table",
            "form",
            "h1",
            "h2",
            "h3",
            "h4",
            "p",
            "div"
        ];

        var nodes = Array.from(document.querySelectorAll(selectors.join(",")));

        var valid = [];

        nodes.forEach(function (el) {
            if (!isVisible(el)) return;
            if (isNavigationLike(el)) return;

            var rect = el.getBoundingClientRect();

            if (rect.bottom <= headerBottom + 10) return;
            if (rect.top < headerBottom - 20 && rect.height < 80) return;

            var txt = normalizeText(el.innerText || el.textContent || "");

            /*
              El texto de botones/navbar no cuenta como contenido.
            */
            var cleaned = txt;

            [
                "orion procesos",
                "gestion diaria orion",
                "gestion diaria aster",
                "consolidar gestion",
                "inicio",
                "logs",
                "reset"
            ].forEach(function (x) {
                cleaned = cleaned.replaceAll(normalizeText(x), "");
            });

            cleaned = normalizeText(cleaned);

            if (cleaned.length >= 8 || rect.height >= 80) {
                valid.push({
                    el: el,
                    text: cleaned,
                    rect: {
                        top: rect.top,
                        bottom: rect.bottom,
                        width: rect.width,
                        height: rect.height
                    }
                });
            }
        });

        return valid;
    }

    function getRealContentText() {
        var elements = getRealContentElements();

        return normalizeText(
            elements
                .map(function (x) { return x.text; })
                .filter(Boolean)
                .join(" ")
        );
    }

    function pageHasRealContent() {
        var elements = getRealContentElements();
        var text = getRealContentText();

        if (text.length >= 15) return true;

        /*
          Si hay un bloque visual grande debajo del header, también cuenta,
          pero solo si no es body/html.
        */
        var hasLargeBlock = elements.some(function (x) {
            var tag = x.el.tagName.toLowerCase();
            if (tag === "body" || tag === "html") return false;
            return x.rect.height >= 120 && x.rect.width >= 300;
        });

        return hasLargeBlock;
    }

    function pageLooksEmpty() {
        return !pageHasRealContent();
    }

    function pageLooksLikeConsolidar() {
        var text = getRealContentText();

        return (
            text.includes("monitor de ejecucion") ||
            text.includes("consolidacion") ||
            text.includes("consolidar") ||
            text.includes("gestion consolidada") ||
            text.includes("orion --") ||
            text.includes("aister --") ||
            text.includes("aster --") ||
            text.includes("sin verificar")
        );
    }

    function repairConsolidarIfNeeded(reason) {
        var now = Date.now();

        var empty = pageLooksEmpty();
        var looksConsolidar = pageLooksLikeConsolidar();

        if (repairing) {
            return {
                ok: false,
                status: "already_repairing",
                version: VERSION,
                empty: empty,
                looksConsolidar: looksConsolidar
            };
        }

        /*
          Esta es la corrección principal contra el falso positivo:
          Solo está visible si hay contenido real debajo del header
          Y ese contenido parece ser de Consolidar.
        */
        if (!empty && looksConsolidar) {
            return {
                ok: true,
                status: "already_visible",
                version: VERSION,
                empty: empty,
                looksConsolidar: looksConsolidar
            };
        }

        if (now - lastRepairAt < 500) {
            return {
                ok: false,
                status: "too_soon",
                version: VERSION,
                empty: empty,
                looksConsolidar: looksConsolidar
            };
        }

        if (repairCount >= MAX_REPAIRS) {
            console.warn("[OrionPanelFix] Límite de reparaciones alcanzado.");
            return {
                ok: false,
                status: "max_repairs_reached",
                version: VERSION,
                empty: empty,
                looksConsolidar: looksConsolidar
            };
        }

        var inicioBtn = findButton("inicio");
        var consolidarBtn = findButton("consolidar");

        if (!inicioBtn || !consolidarBtn) {
            console.warn("[OrionPanelFix] Faltan botones para reparar.", {
                inicio: !!inicioBtn,
                consolidar: !!consolidarBtn
            });

            return {
                ok: false,
                status: "missing_buttons",
                version: VERSION,
                inicio: !!inicioBtn,
                consolidar: !!consolidarBtn,
                empty: empty,
                looksConsolidar: looksConsolidar
            };
        }

        repairing = true;
        lastRepairAt = now;
        repairCount += 1;

        console.warn("[OrionPanelFix] Reparando panel Consolidar: Inicio -> Consolidar.", {
            reason: reason || "manual",
            repairCount: repairCount,
            empty: empty,
            looksConsolidar: looksConsolidar
        });

        clickButton("inicio");

        window.setTimeout(function () {
            clickButton("consolidar");
        }, 300);

        window.setTimeout(function () {
            repairing = false;

            var stillEmpty = pageLooksEmpty();
            var stillLooksConsolidar = pageLooksLikeConsolidar();

            if (stillEmpty || !stillLooksConsolidar) {
                console.warn("[OrionPanelFix] El panel aún no quedó correcto después de reparar.", {
                    stillEmpty: stillEmpty,
                    stillLooksConsolidar: stillLooksConsolidar,
                    realContentText: getRealContentText()
                });
            }
        }, 1200);

        return {
            ok: true,
            status: "repair_started",
            version: VERSION,
            repairCount: repairCount,
            empty: empty,
            looksConsolidar: looksConsolidar
        };
    }

    function scheduleConsolidarCheck() {
        window.setTimeout(function () {
            if (lastAction !== "consolidar") return;

            if (pageLooksEmpty() || !pageLooksLikeConsolidar()) {
                repairConsolidarIfNeeded("check_300ms_after_consolidar");
            }
        }, 300);

        window.setTimeout(function () {
            if (lastAction !== "consolidar") return;

            if (pageLooksEmpty() || !pageLooksLikeConsolidar()) {
                repairConsolidarIfNeeded("check_900ms_after_consolidar");
            }
        }, 900);

        window.setTimeout(function () {
            if (lastAction !== "consolidar") return;

            if (pageLooksEmpty() || !pageLooksLikeConsolidar()) {
                repairConsolidarIfNeeded("check_1600ms_after_consolidar");
            }
        }, 1600);
    }

    document.addEventListener("click", function (event) {
        var trigger = event.target.closest(
            "button, a, [role='button'], input[type='button'], input[type='submit']"
        );

        if (!trigger) return;

        var action = detectActionFromElement(trigger);

        if (!action) return;

        lastAction = action;

        if (action !== "consolidar") {
            repairCount = 0;
        }

        log("click detectado", action);

        if (action === "consolidar") {
            scheduleConsolidarCheck();
        }
    }, true);

    window.OrionPanelFix = {
        version: VERSION,

        findButton: findButton,
        clickButton: clickButton,

        getHeaderBottom: getHeaderBottom,
        getRealContentElements: getRealContentElements,
        getRealContentText: getRealContentText,

        pageHasRealContent: pageHasRealContent,
        pageLooksEmpty: pageLooksEmpty,
        pageLooksLikeConsolidar: pageLooksLikeConsolidar,

        repairConsolidarIfNeeded: repairConsolidarIfNeeded,

        debug: function () {
            return {
                version: VERSION,
                lastAction: lastAction,
                repairing: repairing,
                repairCount: repairCount,
                headerBottom: getHeaderBottom(),
                pageHasRealContent: pageHasRealContent(),
                pageLooksEmpty: pageLooksEmpty(),
                pageLooksLikeConsolidar: pageLooksLikeConsolidar(),
                realContentText: getRealContentText(),
                realContentElements: getRealContentElements().map(function (x) {
                    return {
                        tag: x.el.tagName,
                        id: x.el.id,
                        className: x.el.className,
                        text: x.text,
                        rect: x.rect
                    };
                }),
                buttons: getButtons().map(function (b) {
                    return {
                        text: textOf(b),
                        meta: metaOf(b),
                        action: detectActionFromElement(b)
                    };
                })
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
